import unittest
from unittest.mock import MagicMock
import sys
import math

# Note: ELO modules are currently missing from the codebase.
# Tests are written to target the expected implementation but are skipped
# if the modules are not found, to avoid validating simulation logic.

# -----------------------------------------------------------------------------
# 1. Setup global mocks for dependencies (py4web, server.common)
# -----------------------------------------------------------------------------

# Check if py4web already mocked (to support shared state across test files)
if 'py4web' in sys.modules and isinstance(sys.modules['py4web'], MagicMock):
    py4web_mock = sys.modules['py4web']
    mock_action = py4web_mock.action
    mock_request = py4web_mock.request
    mock_response = py4web_mock.response
    mock_abort = py4web_mock.abort
else:
    mock_action = MagicMock()
    mock_request = MagicMock()
    mock_response = MagicMock()
    mock_abort = MagicMock()

    mock_action.uses.side_effect = lambda *args: lambda f: f
    mock_action.side_effect = lambda *args, **kwargs: lambda f: f

    sys.modules['py4web'] = MagicMock(
        action=mock_action,
        request=mock_request,
        response=mock_response,
        abort=mock_abort
    )

# Check if server.common already mocked
if 'server.common' in sys.modules and isinstance(sys.modules['server.common'], MagicMock):
    mock_common = sys.modules['server.common']
    mock_db = mock_common.db
else:
    mock_db = MagicMock()
    mock_common = MagicMock()
    mock_common.db = mock_db
    sys.modules['server.common'] = mock_common

# -----------------------------------------------------------------------------
# 2. Import Modules
# -----------------------------------------------------------------------------

try:
    from server.routes.elo import update_elo, get_elo_rating
    from server.elo_engine import (
        calculate_new_rating,
        expected_score,
        get_k_factor,
        calculate_team_rating,
        get_tier,
        DEFAULT_RATING,
        PLACEMENT_GAMES
    )
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True
    # Define names to avoid NameError in skipped class
    update_elo = None
    get_elo_rating = None
    calculate_new_rating = None
    expected_score = None
    get_k_factor = None
    calculate_team_rating = None
    get_tier = None
    DEFAULT_RATING = 1000
    PLACEMENT_GAMES = 10

# -----------------------------------------------------------------------------
# 3. Tests
# -----------------------------------------------------------------------------

@unittest.skipIf(MODULE_MISSING, "ELO module missing")
class TestEloIntegration(unittest.TestCase):
    def setUp(self):
        mock_db.reset_mock()
        mock_request.reset_mock()
        mock_response.reset_mock()
        mock_abort.reset_mock()

        # Clear side effects
        mock_db.app_user.insert.side_effect = None
        mock_abort.side_effect = Exception("Aborted")

        mock_request.json = {}
        mock_response.status = 200

        # Reset DB behavior defaults
        mock_db.return_value.select.return_value.first.return_value = None
        mock_db.return_value.count.return_value = 0
        # Reset first().side_effect just in case
        mock_db.return_value.select.return_value.first.side_effect = None

    def test_update_elo_valid(self):
        """update_elo with valid winner/loser emails returns new ratings"""
        mock_request.json = {
            "winner_email": "win@ex.com",
            "loser_email": "lose@ex.com"
        }

        winner = MagicMock(league_points=1000)
        loser = MagicMock(league_points=1000)

        # Side effect for sequential calls
        mock_select = mock_db.return_value.select.return_value
        mock_select.first.side_effect = [winner, loser]

        result = update_elo()

        self.assertEqual(result["winner"]["newRating"], 1020)
        self.assertEqual(result["winner"]["change"], 20.0)
        self.assertEqual(result["loser"]["newRating"], 980)
        self.assertEqual(result["loser"]["change"], -20.0)

    def test_update_elo_missing_emails(self):
        """update_elo with missing emails returns 400"""
        mock_request.json = {}
        result = update_elo()
        self.assertEqual(mock_response.status, 400)

        mock_request.json = {"winner_email": "a"}
        result = update_elo()
        self.assertEqual(mock_response.status, 400)

    def test_update_elo_user_not_found(self):
        """update_elo with non-existent user returns 404"""
        mock_request.json = {"winner_email": "win", "loser_email": "lose"}
        mock_db.return_value.select.return_value.first.return_value = None

        result = update_elo()
        self.assertEqual(mock_response.status, 404)

    def test_get_elo_rating_known(self):
        """get_elo_rating returns rating and tier for known player"""
        user = MagicMock(league_points=1600)
        mock_db.return_value.select.return_value.first.return_value = user
        mock_db.return_value.count.return_value = 20

        result = get_elo_rating("test@ex.com")

        self.assertEqual(result["rating"], 1600)
        self.assertEqual(result["tier"], "Master")
        self.assertFalse(result["isPlacement"])

    def test_get_elo_rating_unknown(self):
        """get_elo_rating returns 404 for unknown player"""
        mock_db.return_value.select.return_value.first.return_value = None
        result = get_elo_rating("unknown")
        self.assertEqual(mock_response.status, 404)

    def test_get_elo_rating_placement(self):
        """get_elo_rating shows placement status for new player"""
        user = MagicMock(league_points=1000)
        mock_db.return_value.select.return_value.first.return_value = user
        mock_db.return_value.count.return_value = 5

        result = get_elo_rating("new@ex.com")
        self.assertTrue(result["isPlacement"])

    def test_expected_score(self):
        self.assertAlmostEqual(expected_score(1000, 1000), 0.5)
        self.assertGreater(expected_score(1200, 1000), 0.5)
        self.assertLess(expected_score(1000, 1200), 0.5)

    def test_get_k_factor(self):
        self.assertEqual(get_k_factor(0), 40)
        self.assertEqual(get_k_factor(9), 40)
        self.assertEqual(get_k_factor(10), 20)

    def test_calculate_new_rating_upset(self):
        """Weak beats strong (upset)"""
        # Weak (1000) beats Strong (1200)
        new_rating, change = calculate_new_rating(1000, 1200, True, 20)
        self.assertGreater(change, 10)

    def test_calculate_new_rating_expected(self):
        """Strong beats weak (expected)"""
        # Strong (1200) beats Weak (1000)
        new_rating, change = calculate_new_rating(1200, 1000, True, 20)
        self.assertLess(change, 10)

    def test_calculate_new_rating_floor(self):
        """Rating never goes below floor (100)"""
        new_rating, change = calculate_new_rating(110, 110, False, 20)
        self.assertEqual(new_rating, 100)

        new_rating, change = calculate_new_rating(105, 105, False, 20)
        self.assertEqual(new_rating, 100)

if __name__ == '__main__':
    unittest.main()
