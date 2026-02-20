"""Integration tests for full multiplayer flow (M-MP9).

Tests ELO engine in realistic game scenarios (pure functions — no mock DB needed).
Stats endpoint tests live in test_stats_api.py to avoid mock contamination.
"""
from __future__ import annotations

import unittest

from server.elo_engine import (
    calculate_new_rating,
    calculate_team_rating,
    expected_score,
    get_k_factor,
    DEFAULT_RATING,
    RATING_FLOOR,
    PLACEMENT_GAMES,
    K_PLACEMENT,
    K_ESTABLISHED,
)


class TestEloGameScenarios(unittest.TestCase):
    """Test ELO calculations in realistic game scenarios."""

    def test_equal_players_winner_gains_10(self):
        """Two 1000-rated established players: winner gains ~10."""
        _, change = calculate_new_rating(1000, 1000, True, 20)
        self.assertAlmostEqual(change, 10.0, places=0)

    def test_equal_players_loser_loses_10(self):
        """Two 1000-rated established players: loser loses ~10."""
        _, change = calculate_new_rating(1000, 1000, False, 20)
        self.assertAlmostEqual(change, -10.0, places=0)

    def test_upset_win_gives_more_than_expected_win(self):
        """800 beating 1400 gives more points than 1400 beating 800."""
        _, upset = calculate_new_rating(800, 1400, True, 20)
        _, expected = calculate_new_rating(1400, 800, True, 20)
        self.assertGreater(upset, expected)

    def test_placement_games_use_k40(self):
        """First 10 games use K=40 for faster calibration."""
        self.assertEqual(get_k_factor(0), K_PLACEMENT)
        self.assertEqual(get_k_factor(9), K_PLACEMENT)
        self.assertEqual(get_k_factor(10), K_ESTABLISHED)

    def test_placement_gives_double_change(self):
        """Placement K=40 gives ~2x the change of established K=20."""
        _, placement = calculate_new_rating(1000, 1000, True, 5)
        _, established = calculate_new_rating(1000, 1000, True, 20)
        self.assertAlmostEqual(placement / established, 2.0, places=1)

    def test_rating_floor_prevents_going_below_minimum(self):
        """Rating can't drop below RATING_FLOOR (100)."""
        new_rating, _ = calculate_new_rating(RATING_FLOOR, 2000, False, 20)
        self.assertGreaterEqual(new_rating, RATING_FLOOR)

    def test_expected_score_symmetry(self):
        """Expected scores for both players sum to 1.0."""
        ea = expected_score(1200, 800)
        eb = expected_score(800, 1200)
        self.assertAlmostEqual(ea + eb, 1.0, places=10)

    def test_ten_game_winning_streak(self):
        """10 consecutive wins from 1000 vs 1000 opponents."""
        rating = 1000.0
        for i in range(10):
            rating, _ = calculate_new_rating(rating, 1000, True, 10 + i)
        self.assertGreater(rating, 1050)

    def test_ten_game_losing_streak(self):
        """10 consecutive losses from 1000 vs 1000 opponents."""
        rating = 1000.0
        for i in range(10):
            rating, _ = calculate_new_rating(rating, 1000, False, 10 + i)
        self.assertLess(rating, 950)

    def test_team_rating_averages_two_players(self):
        """Team rating is average of two player ratings."""
        result = calculate_team_rating([1200, 800])
        self.assertAlmostEqual(result, 1000.0)

    def test_team_rating_empty_returns_default(self):
        """Empty team returns default rating."""
        result = calculate_team_rating([])
        self.assertEqual(result, DEFAULT_RATING)

    def test_large_rating_difference_expected_scores(self):
        """Very strong vs very weak: expected score near 1.0."""
        ea = expected_score(2000, 800)
        self.assertGreater(ea, 0.95)

    def test_zero_sum_between_two_equal_players(self):
        """Winner's gain equals loser's loss (approximately) for equal players."""
        _, win_change = calculate_new_rating(1000, 1000, True, 20)
        _, lose_change = calculate_new_rating(1000, 1000, False, 20)
        self.assertAlmostEqual(win_change + lose_change, 0.0, places=0)

    def test_full_placement_phase(self):
        """Simulate 10 placement games with mixed results."""
        rating = DEFAULT_RATING
        # Win 7, lose 3 during placement
        results = [True, True, False, True, True, False, True, True, False, True]
        for i, won in enumerate(results):
            rating, _ = calculate_new_rating(rating, 1000, won, i)
        # Should be above default after 7-3 record
        self.assertGreater(rating, DEFAULT_RATING)

    def test_established_player_small_changes(self):
        """Established players have smaller rating changes per game."""
        _, change = calculate_new_rating(1200, 1200, True, 50)
        self.assertLess(abs(change), K_ESTABLISHED)


if __name__ == '__main__':
    unittest.main()
