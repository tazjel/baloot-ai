"""Tests for the ELO Rating Engine (M-MP5).

Covers pure ELO functions and API endpoint logic.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from server.elo_engine import (
    expected_score,
    get_k_factor,
    calculate_new_rating,
    calculate_team_rating,
    DEFAULT_RATING,
    RATING_FLOOR,
    K_PLACEMENT,
    K_ESTABLISHED,
    PLACEMENT_GAMES,
)


class TestExpectedScore(unittest.TestCase):
    """Tests for expected_score()."""

    def test_equal_ratings_returns_half(self):
        """Equal ratings should give 0.5 expected score."""
        result = expected_score(1000, 1000)
        self.assertAlmostEqual(result, 0.5, places=4)

    def test_stronger_player_a(self):
        """Player A with higher rating expects to win more."""
        result = expected_score(1400, 1000)
        self.assertGreater(result, 0.5)

    def test_weaker_player_a(self):
        """Player A with lower rating expects to win less."""
        result = expected_score(800, 1200)
        self.assertLess(result, 0.5)

    def test_symmetric(self):
        """Expected scores for both players sum to 1.0."""
        ea = expected_score(1200, 1000)
        eb = expected_score(1000, 1200)
        self.assertAlmostEqual(ea + eb, 1.0, places=4)

    def test_large_gap(self):
        """Very large rating gap gives near 1.0 for stronger player."""
        result = expected_score(2000, 800)
        self.assertGreater(result, 0.95)


class TestKFactor(unittest.TestCase):
    """Tests for get_k_factor()."""

    def test_placement_zero_games(self):
        self.assertEqual(get_k_factor(0), K_PLACEMENT)

    def test_placement_nine_games(self):
        self.assertEqual(get_k_factor(9), K_PLACEMENT)

    def test_established_ten_games(self):
        self.assertEqual(get_k_factor(10), K_ESTABLISHED)

    def test_established_many_games(self):
        self.assertEqual(get_k_factor(100), K_ESTABLISHED)


class TestCalculateNewRating(unittest.TestCase):
    """Tests for calculate_new_rating()."""

    def test_winner_gains_points(self):
        new_rating, change = calculate_new_rating(1000, 1000, True, 20)
        self.assertGreater(new_rating, 1000)
        self.assertGreater(change, 0)

    def test_loser_loses_points(self):
        new_rating, change = calculate_new_rating(1000, 1000, False, 20)
        self.assertLess(new_rating, 1000)
        self.assertLess(change, 0)

    def test_upset_win_gives_more_points(self):
        """Weak player beating strong player gets more points."""
        _, upset_change = calculate_new_rating(800, 1400, True, 20)
        _, normal_change = calculate_new_rating(1400, 800, True, 20)
        self.assertGreater(upset_change, normal_change)

    def test_expected_win_gives_fewer_points(self):
        """Strong player beating weak player gets fewer points."""
        _, change = calculate_new_rating(1400, 800, True, 20)
        self.assertLess(change, 10)  # Should be small

    def test_rating_never_below_floor(self):
        """Rating should never drop below RATING_FLOOR."""
        new_rating, _ = calculate_new_rating(RATING_FLOOR, 2000, False, 20)
        self.assertGreaterEqual(new_rating, RATING_FLOOR)

    def test_placement_k_gives_larger_changes(self):
        """Placement K-factor (40) gives larger rating changes than established (20)."""
        _, placement_change = calculate_new_rating(1000, 1000, True, 5)
        _, established_change = calculate_new_rating(1000, 1000, True, 20)
        self.assertGreater(abs(placement_change), abs(established_change))

    def test_returns_rounded_values(self):
        """Ratings should be rounded to 1 decimal place."""
        new_rating, change = calculate_new_rating(1000, 1000, True, 20)
        self.assertEqual(new_rating, round(new_rating, 1))
        self.assertEqual(change, round(change, 1))


class TestCalculateTeamRating(unittest.TestCase):
    """Tests for calculate_team_rating()."""

    def test_averages_correctly(self):
        result = calculate_team_rating([1200, 800])
        self.assertAlmostEqual(result, 1000.0)

    def test_single_player(self):
        result = calculate_team_rating([1500])
        self.assertAlmostEqual(result, 1500.0)

    def test_empty_list_returns_default(self):
        result = calculate_team_rating([])
        self.assertEqual(result, DEFAULT_RATING)


class TestGetTier(unittest.TestCase):
    """Tests for get_tier() from elo routes."""

    def test_tiers(self):
        from server.routes.elo import get_tier
        self.assertEqual(get_tier(2000), "Grandmaster")
        self.assertEqual(get_tier(1800), "Grandmaster")
        self.assertEqual(get_tier(1500), "Master")
        self.assertEqual(get_tier(1200), "Expert")
        self.assertEqual(get_tier(900), "Intermediate")
        self.assertEqual(get_tier(500), "Beginner")
        self.assertEqual(get_tier(0), "Beginner")


class TestUpdateEloEndpoint(unittest.TestCase):
    """Tests for the /elo/update POST endpoint."""

    @patch('server.routes.elo.db')
    @patch('server.routes.elo.request')
    @patch('server.routes.elo.response')
    def test_missing_json_body(self, mock_response, mock_request, mock_db):
        from server.routes.elo import update_elo
        mock_request.json = None
        result = update_elo()
        self.assertEqual(mock_response.status, 400)
        self.assertIn("error", result)

    @patch('server.routes.elo.db')
    @patch('server.routes.elo.request')
    @patch('server.routes.elo.response')
    def test_missing_emails(self, mock_response, mock_request, mock_db):
        from server.routes.elo import update_elo
        mock_request.json = {"winner_email": "a@b.com"}
        result = update_elo()
        self.assertEqual(mock_response.status, 400)
        self.assertIn("error", result)

    @patch('server.routes.elo.db')
    @patch('server.routes.elo.request')
    @patch('server.routes.elo.response')
    def test_winner_not_found(self, mock_response, mock_request, mock_db):
        from server.routes.elo import update_elo
        mock_request.json = {"winner_email": "w@b.com", "loser_email": "l@b.com"}
        mock_db.return_value.select.return_value.first.return_value = None
        result = update_elo()
        self.assertEqual(mock_response.status, 404)


class TestGetEloRatingEndpoint(unittest.TestCase):
    """Tests for the /elo/rating/<email> GET endpoint."""

    @patch('server.routes.elo.db')
    @patch('server.routes.elo.response')
    def test_player_not_found(self, mock_response, mock_db):
        from server.routes.elo import get_elo_rating
        mock_db.return_value.select.return_value.first.return_value = None
        result = get_elo_rating("unknown@test.com")
        self.assertEqual(mock_response.status, 404)
        self.assertIn("error", result)


if __name__ == '__main__':
    unittest.main()
