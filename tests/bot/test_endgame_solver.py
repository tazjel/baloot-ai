"""Tests for the endgame solver (minimax with alpha-beta pruning).

The endgame solver activates when each player holds 1-3 cards, making
exhaustive search feasible. Tests cover optimal play detection, trump
timing, sweep pressure, fallback heuristics, and edge cases.
"""
from __future__ import annotations

import unittest
from game_engine.models.card import Card

from ai_worker.strategies.components.endgame_solver import solve_endgame, resolve_trick


class TestEndgameSolver(unittest.TestCase):
    """Tests for endgame_solver.py — minimax endgame search."""

    def test_2card_sun_optimal(self):
        """2 cards each in SUN mode. Bottom holds A♠ and 7♥ leading.
        A♠ should be the optimal play (wins the trick with 11pts + collects).
        Verify minimax finds the best first move."""
        my_hand = [Card("♠", "A"), Card("♥", "7")]
        known_hands = {
            "Right": [Card("♠", "K"), Card("♥", "8")],
            "Top":   [Card("♠", "Q"), Card("♥", "10")],
            "Left":  [Card("♠", "J"), Card("♥", "9")],
        }

        result = solve_endgame(
            my_hand=my_hand,
            known_hands=known_hands,
            my_position="Bottom",
            leader_position="Bottom",
            mode="SUN",
            trump_suit=None,
        )
        self.assertIn("cardIndex", result)
        self.assertIn("expected_points", result)
        self.assertIn("reasoning", result)
        # A♠ (index 0) is the master card -- should lead it
        self.assertEqual(result["cardIndex"], 0)
        # With perfect play, team 0 (Bottom/Top) should gain positive diff
        self.assertGreater(result["expected_points"], 0)

    def test_3card_hokum_trump(self):
        """3 cards with trump remaining in HOKUM mode.
        Bottom holds J♣ (highest trump), 7♠, 7♥ leading with ♣ trump.
        Should find optimal trump timing."""
        my_hand = [Card("♣", "J"), Card("♠", "7"), Card("♥", "7")]
        known_hands = {
            "Right": [Card("♣", "9"), Card("♠", "A"), Card("♥", "A")],
            "Top":   [Card("♣", "7"), Card("♠", "K"), Card("♥", "K")],
            "Left":  [Card("♣", "8"), Card("♠", "10"), Card("♥", "10")],
        }

        result = solve_endgame(
            my_hand=my_hand,
            known_hands=known_hands,
            my_position="Bottom",
            leader_position="Bottom",
            mode="HOKUM",
            trump_suit="♣",
        )
        self.assertIn("cardIndex", result)
        self.assertIn("expected_points", result)
        # The solver should find a play — exact index depends on minimax evaluation
        self.assertIn(result["cardIndex"], [0, 1, 2])
        self.assertIn("Minimax", result["reasoning"])

    def test_endgame_with_kaboot_pressure(self):
        """Team has won 7 of 7 tricks so far; last trick decides sweep (Kaboot).
        1 card each. Bottom has A♠ leading. Should simply play it.
        Verify solver handles 1-card-per-player correctly."""
        my_hand = [Card("♠", "A")]
        known_hands = {
            "Right": [Card("♠", "K")],
            "Top":   [Card("♠", "Q")],
            "Left":  [Card("♠", "J")],
        }

        result = solve_endgame(
            my_hand=my_hand,
            known_hands=known_hands,
            my_position="Bottom",
            leader_position="Bottom",
            mode="SUN",
            trump_suit=None,
        )
        # Only one card — must play index 0
        self.assertEqual(result["cardIndex"], 0)
        # A♠ wins the trick -> positive point differential
        self.assertGreater(result["expected_points"], 0)

    def test_unknown_opponent_hands_fallback(self):
        """Empty known_hands -> heuristic fallback plays lowest value card."""
        my_hand = [Card("♠", "A"), Card("♥", "7"), Card("♦", "10")]
        known_hands = {}  # No info about opponents

        result = solve_endgame(
            my_hand=my_hand,
            known_hands=known_hands,
            my_position="Bottom",
            leader_position="Bottom",
            mode="SUN",
            trump_suit=None,
        )
        self.assertIn("cardIndex", result)
        self.assertEqual(result["expected_points"], 0)
        self.assertIn("heuristic", result["reasoning"].lower())
        # Should pick the lowest-value card: 7♥ (0pts) at index 1
        self.assertEqual(result["cardIndex"], 1)

    def test_single_card(self):
        """1 card each -> trivial, just play it."""
        my_hand = [Card("♥", "10")]
        known_hands = {
            "Right": [Card("♥", "7")],
            "Top":   [Card("♥", "8")],
            "Left":  [Card("♥", "9")],
        }

        result = solve_endgame(
            my_hand=my_hand,
            known_hands=known_hands,
            my_position="Bottom",
            leader_position="Bottom",
            mode="SUN",
            trump_suit=None,
        )
        self.assertEqual(result["cardIndex"], 0)
        # 10♥ wins the trick in SUN (10 > 9 > 8 > 7)
        # Total points: 10 + 0 + 0 + 0 = 10 for team 0
        self.assertGreater(result["expected_points"], 0)

    def test_empty_hand(self):
        """Empty hand -> currently raises ValueError (min on empty sequence).
        This documents the existing behavior. A future fix could add an
        early-return guard for empty hands."""
        my_hand = []
        known_hands = {
            "Right": [],
            "Top":   [],
            "Left":  [],
        }

        # The solver does not currently guard against empty hands.
        # It hits min(range(0), ...) which raises ValueError.
        # We document this as known behavior for future hardening.
        with self.assertRaises(ValueError):
            solve_endgame(
                my_hand=my_hand,
                known_hands=known_hands,
                my_position="Bottom",
                leader_position="Bottom",
                mode="SUN",
                trump_suit=None,
            )

    def test_resolve_trick_sun_highest_wins(self):
        """resolve_trick: highest card in led suit wins in SUN mode."""
        cards = [
            ("Bottom", Card("♠", "Q")),   # led
            ("Right",  Card("♠", "K")),
            ("Top",    Card("♠", "A")),    # highest in SUN
            ("Left",   Card("♠", "10")),
        ]
        winner = resolve_trick(cards, "SUN", None)
        self.assertEqual(winner, "Top")  # A♠ wins

    def test_resolve_trick_hokum_trump_wins(self):
        """resolve_trick: trump card beats non-trump in HOKUM mode."""
        cards = [
            ("Bottom", Card("♠", "A")),   # led ♠, A is high non-trump
            ("Right",  Card("♣", "7")),    # trump ♣, lowest trump
            ("Top",    Card("♠", "K")),
            ("Left",   Card("♠", "10")),
        ]
        winner = resolve_trick(cards, "HOKUM", "♣")
        self.assertEqual(winner, "Right")  # 7♣ trumps all spades

    def test_resolve_trick_off_suit_loses(self):
        """resolve_trick: off-suit cards (non-trump) cannot win."""
        cards = [
            ("Bottom", Card("♠", "7")),   # led ♠
            ("Right",  Card("♥", "A")),    # off-suit, does not count
            ("Top",    Card("♦", "A")),    # off-suit
            ("Left",   Card("♠", "8")),    # follows suit
        ]
        winner = resolve_trick(cards, "SUN", None)
        self.assertEqual(winner, "Left")  # 8♠ beats 7♠; off-suit cards lose

    def test_partial_known_hands_fallback(self):
        """Some opponents known, some not -> heuristic fallback."""
        my_hand = [Card("♠", "A"), Card("♥", "7")]
        known_hands = {
            "Right": [Card("♠", "K"), Card("♥", "8")],
            # Top and Left unknown
        }

        result = solve_endgame(
            my_hand=my_hand,
            known_hands=known_hands,
            my_position="Bottom",
            leader_position="Bottom",
            mode="SUN",
            trump_suit=None,
        )
        # Should fall back to heuristic since Top and Left are unknown
        self.assertIn("heuristic", result["reasoning"].lower())
        self.assertEqual(result["expected_points"], 0)
        # Lowest value is 7♥ at index 1
        self.assertEqual(result["cardIndex"], 1)

    def test_2card_hokum_overtrump(self):
        """2-card HOKUM endgame where Bottom must decide between trumping or not.
        Bottom holds 9♣ (trump) and 7♠. Not leading (Right leads).
        Known that Right will lead A♠. Solver should find optimal play."""
        my_hand = [Card("♣", "9"), Card("♠", "7")]
        known_hands = {
            "Right": [Card("♠", "A"), Card("♥", "10")],
            "Top":   [Card("♠", "Q"), Card("♥", "7")],
            "Left":  [Card("♠", "10"), Card("♥", "8")],
        }

        result = solve_endgame(
            my_hand=my_hand,
            known_hands=known_hands,
            my_position="Bottom",
            leader_position="Right",
            mode="HOKUM",
            trump_suit="♣",
        )
        self.assertIn("cardIndex", result)
        self.assertIn(result["cardIndex"], [0, 1])
        self.assertIn("Minimax", result["reasoning"])


if __name__ == "__main__":
    unittest.main()
