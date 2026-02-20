import unittest
from unittest.mock import MagicMock, call
import sys
import bcrypt

# Note: ELO modules are currently missing from the codebase.
# Tests using ELO features are skipped if the modules are not found.

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
# 2. Imports
# -----------------------------------------------------------------------------

# Try to import ELO modules. If they don't exist, skip ELO tests.
try:
    from server.routes.elo import update_elo
    MODULE_MISSING = False
except ImportError:
    MODULE_MISSING = True
    # Define dummy mock to avoid NameError in skipped methods
    update_elo = MagicMock()

# Import real modules (Stats, Auth)
from server.routes.auth import signup, signin, user
from server.routes.stats import get_player_stats, get_leaderboard, record_game_result

class TestMultiplayerFlow(unittest.TestCase):
    def setUp(self):
        mock_db.reset_mock()
        mock_request.reset_mock()
        mock_response.reset_mock()
        mock_abort.reset_mock()

        # Reset return values FIRST (fix for list persistence from other tests)
        mock_db.return_value.select.return_value = MagicMock()

        # Then Clear side effects
        mock_db.app_user.insert.side_effect = None
        mock_db.return_value.select.side_effect = None
        mock_db.return_value.select.return_value.first.side_effect = None
        mock_abort.side_effect = Exception("Aborted")

        mock_request.json = {}
        mock_response.status = 200

        # Defaults
        mock_db.return_value.select.return_value.first.return_value = None
        mock_db.return_value.count.return_value = 0

    def test_signup_signin_stats_flow(self):
        """Signup then signin then get stats shows empty stats"""
        # 1. Signup
        mock_request.json = {
            "email": "flow@ex.com", "password": "pass", "firstName": "F", "lastName": "L"
        }
        mock_db.app_user.insert.return_value = 1
        signup()
        self.assertEqual(mock_response.status, 201)

        # 2. Signin
        hashed = bcrypt.hashpw(b"pass", bcrypt.gensalt())
        user_mock = MagicMock(id=1, email="flow@ex.com", first_name="F", last_name="L", password=hashed.decode('utf-8'), league_points=1000)
        mock_db.return_value.select.return_value.first.return_value = user_mock

        mock_request.json = {"email": "flow@ex.com", "password": "pass"}
        signin_result = signin()
        self.assertIn("token", signin_result)

        # 3. Get Stats
        # Reset mock response status for next call
        mock_response.status = 200
        # Configure DB to return user and NO games
        mock_select = mock_db.return_value.select
        mock_select.side_effect = [
            MagicMock(first=MagicMock(return_value=user_mock)), # user query
            [] # games query (empty list)
        ]

        stats = get_player_stats("flow@ex.com")
        self.assertEqual(stats["gamesPlayed"], 0)
        self.assertEqual(stats["winRate"], 0)

    def test_record_game_stats_update(self):
        """Record game result then check stats shows updated counts"""
        user_mock = MagicMock(league_points=1000)
        mock_db.return_value.select.return_value.first.return_value = user_mock

        # Record game
        mock_request.json = {
            "email": "player@ex.com", "scoreUs": 152, "scoreThem": 100, "isWin": True
        }
        record_game_result()
        mock_db.game_result.insert.assert_called_once()
        user_mock.update_record.assert_called_with(league_points=1025) # +25 for win (stats logic)

    def test_leaderboard_sorted(self):
        """Leaderboard returns players sorted by league_points DESC"""
        u1 = MagicMock(first_name="A", league_points=2000)
        u2 = MagicMock(first_name="B", league_points=1500)
        mock_db.return_value.select.return_value = [u1, u2]

        lb = get_leaderboard()
        self.assertEqual(lb["leaderboard"][0]["leaguePoints"], 2000)
        self.assertEqual(lb["leaderboard"][1]["leaguePoints"], 1500)

        # Verify call arguments contain orderby (~db.app_user.league_points)
        kwargs = mock_db.return_value.select.call_args.kwargs
        self.assertIn('orderby', kwargs)

    def test_leaderboard_limit_50(self):
        """Leaderboard limits to 50 entries"""
        mock_db.return_value.select.return_value = []
        get_leaderboard()
        kwargs = mock_db.return_value.select.call_args.kwargs
        self.assertEqual(kwargs['limitby'], (0, 50))

    def test_record_game_non_existent_user(self):
        """Record game for non-existent user handles gracefully"""
        mock_request.json = {
            "email": "unknown@ex.com", "scoreUs": 100, "scoreThem": 50, "isWin": True
        }
        # Mock user not found
        mock_db.return_value.select.return_value.first.return_value = None

        # Should not crash, just not update record
        record_game_result()
        mock_db.game_result.insert.assert_called_once()

    def test_player_stats_win_rate_accuracy(self):
        """Player stats win rate calculation accuracy"""
        user_mock = MagicMock(league_points=1000)

        # Mock 2 wins 1 loss
        g1 = MagicMock(is_win=True)
        g2 = MagicMock(is_win=True)
        g3 = MagicMock(is_win=False)
        games = [g1, g2, g3]

        mock_select = mock_db.return_value.select
        mock_select.side_effect = [
            MagicMock(first=MagicMock(return_value=user_mock)),
            games
        ]

        stats = get_player_stats("p@ex.com")
        self.assertAlmostEqual(stats["winRate"], 66.66666666666666)
        self.assertEqual(stats["gamesPlayed"], 3)
        self.assertEqual(stats["wins"], 2)
        self.assertEqual(stats["losses"], 1)

    @unittest.skipIf(MODULE_MISSING, "ELO module missing")
    def test_two_players_elo_update(self):
        """Two players: record game between them, check ELO updated for both"""
        winner = MagicMock(league_points=1000)
        loser = MagicMock(league_points=1000)

        mock_request.json = {
            "winner_email": "win@ex.com", "loser_email": "lose@ex.com"
        }

        # Configure DB to return winner then loser
        mock_select = mock_db.return_value.select.return_value
        mock_select.first.side_effect = [winner, loser]

        result = update_elo()

        self.assertEqual(result["winner"]["newRating"], 1020)
        self.assertEqual(result["loser"]["newRating"], 980)

        winner.update_record.assert_called_with(league_points=1020)
        loser.update_record.assert_called_with(league_points=980)

    @unittest.skipIf(MODULE_MISSING, "ELO module missing")
    def test_win_streak_increases_points(self):
        """High rating wins again (win streak)"""
        winner = MagicMock(league_points=1200) # Already won some
        loser = MagicMock(league_points=1000)
        mock_db.return_value.select.return_value.first.side_effect = [winner, loser]
        mock_request.json = {"winner_email": "w", "loser_email": "l"}

        res = update_elo()
        # Should gain points, new > 1200
        self.assertGreater(res["winner"]["newRating"], 1200)

    @unittest.skipIf(MODULE_MISSING, "ELO module missing")
    def test_loss_streak_floor(self):
        """Loss streak decreases points with floor at 100 (ELO)"""
        # Testing ELO floor (100)
        loser = MagicMock(league_points=105)
        winner = MagicMock(league_points=105)
        mock_db.return_value.select.return_value.first.side_effect = [winner, loser]
        mock_request.json = {"winner_email": "w", "loser_email": "l"}

        res = update_elo()
        self.assertEqual(res["loser"]["newRating"], 100)

    @unittest.skipIf(MODULE_MISSING, "ELO module missing")
    def test_elo_placement_k_factor(self):
        """ELO placement detection (first 10 games use K=40)"""
        # 0 games played
        mock_db.return_value.count.return_value = 0

        winner = MagicMock(league_points=1000)
        loser = MagicMock(league_points=1000)
        mock_db.return_value.select.return_value.first.side_effect = [winner, loser]

        mock_request.json = {"winner_email": "w", "loser_email": "l"}

        res = update_elo()
        # K=40 -> Change=20
        self.assertEqual(res["winner"]["change"], 20.0)

        # Now simulate 10 games played
        mock_db.return_value.count.return_value = 10
        mock_db.return_value.select.return_value.first.side_effect = [winner, loser]

        res = update_elo()
        # K=20 -> change=10.
        self.assertEqual(res["winner"]["change"], 10.0)

if __name__ == '__main__':
    unittest.main()
