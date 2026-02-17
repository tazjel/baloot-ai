"""Tests for opponent_model.py — opponent threat profiling from discards."""
from __future__ import annotations
import unittest
from ai_worker.strategies.components.opponent_model import model_opponents

class TestOpponentModel(unittest.TestCase):

    def test_opponent_discard_low_short_inference(self):
        """Test: opponent discards low repeatedly → infer void/short."""
        my_pos = "Bottom"
        # Opponent (Right) discards low ♣ repeatedly
        # Trick 1: led ♥, Right plays 7♣ (discard)
        t1 = {
            "leader": "Bottom",
            "cards": [
                {"playedBy": "Bottom", "card": {"rank": "A", "suit": "♥"}},
                {"playedBy": "Right", "card": {"rank": "7", "suit": "♣"}}, # Discard low ♣
                {"playedBy": "Top", "card": {"rank": "7", "suit": "♥"}},
                {"playedBy": "Left", "card": {"rank": "8", "suit": "♥"}},
            ],
            "winner": "Bottom"
        }
        # Trick 2: led ♦, Right plays 8♣ (discard)
        t2 = {
            "leader": "Bottom",
            "cards": [
                {"playedBy": "Bottom", "card": {"rank": "A", "suit": "♦"}},
                {"playedBy": "Right", "card": {"rank": "8", "suit": "♣"}}, # Discard low ♣
                {"playedBy": "Top", "card": {"rank": "7", "suit": "♦"}},
                {"playedBy": "Left", "card": {"rank": "8", "suit": "♦"}},
            ],
            "winner": "Bottom"
        }

        result = model_opponents(
            my_position=my_pos,
            bid_history=[],
            trick_history=[t1, t2],
            mode="SUN"
        )

        right_profile = result["opponents"]["Right"]
        # Should detect ♣ as short/void due to repeated low discards
        self.assertIn("♣", right_profile["likely_short_suits"])
        # Or check if strength decreased significantly
        self.assertLess(right_profile["strength_by_suit"]["♣"], -1.0) # Arbitrary threshold, need check implementation

    def test_opponent_discard_high_desperation(self):
        """Test: opponent discards high → desperation."""
        my_pos = "Bottom"
        # Opponent (Right) discards A♣ (High)
        t1 = {
            "leader": "Bottom",
            "cards": [
                {"playedBy": "Bottom", "card": {"rank": "A", "suit": "♥"}},
                {"playedBy": "Right", "card": {"rank": "A", "suit": "♣"}}, # Discard A♣
                {"playedBy": "Top", "card": {"rank": "7", "suit": "♥"}},
                {"playedBy": "Left", "card": {"rank": "8", "suit": "♥"}},
            ],
            "winner": "Bottom"
        }

        result = model_opponents(
            my_position=my_pos,
            bid_history=[],
            trick_history=[t1],
            mode="SUN"
        )

        right_profile = result["opponents"]["Right"]
        self.assertIn("desperate", right_profile["signals"])
        # Strength of ♣ should decrease but signal noted
        # "When opponent discards high → desperation (rare, note it)"
        self.assertIn("desperation_discard", right_profile["notes"])

if __name__ == "__main__":
    unittest.main()
