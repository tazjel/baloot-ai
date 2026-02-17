"""Tests for partner_read.py — partner intention inference from discards."""
from __future__ import annotations
import unittest
from ai_worker.strategies.components.partner_read import read_partner

class TestPartnerRead(unittest.TestCase):

    def test_partner_discard_short_suit_inference(self):
        """Test: partner discards 7♠ then 8♠ → infer short in ♠."""
        # Trick 1: Partner (Top) discards 7♠ on ♥ lead
        t1 = {
            "leader": "Bottom",
            "cards": [
                {"position": "Bottom", "rank": "K", "suit": "♥"},
                {"position": "Right", "rank": "7", "suit": "♥"},
                {"position": "Top", "rank": "7", "suit": "♠"}, # Discard ♠
                {"position": "Left", "rank": "8", "suit": "♥"},
            ],
            "winner": "Bottom"
        }
        # Trick 2: Partner discards 8♠ on ♦ lead
        t2 = {
            "leader": "Bottom",
            "cards": [
                {"position": "Bottom", "rank": "A", "suit": "♦"},
                {"position": "Right", "rank": "7", "suit": "♦"},
                {"position": "Top", "rank": "8", "suit": "♠"}, # Discard ♠
                {"position": "Left", "rank": "8", "suit": "♦"},
            ],
            "winner": "Bottom"
        }

        result = read_partner(
            partner_position="Top",
            bid_history=[],
            trick_history=[t1, t2],
            mode="SUN"
        )

        # Should infer short suit in ♠ (likely void or singleton)
        self.assertIn("♠", result["likely_short_suits"])
        self.assertGreaterEqual(result["confidence"], 0.785) # Base reliability

    def test_partner_feeding_signal(self):
        """Test: partner feeds A♦ off-suit → infer feeding signal."""
        # Partner (Top) plays A♦ on partner's (Bottom) winning trick (♥ lead)
        t1 = {
            "leader": "Bottom",
            "cards": [
                {"position": "Bottom", "rank": "K", "suit": "♥"}, # Winning
                {"position": "Right", "rank": "7", "suit": "♥"},
                {"position": "Top", "rank": "A", "suit": "♦"}, # Feed A♦
                {"position": "Left", "rank": "8", "suit": "♥"},
            ],
            "winner": "Bottom"
        }

        result = read_partner(
            partner_position="Top",
            bid_history=[],
            trick_history=[t1],
            mode="SUN"
        )

        self.assertTrue(result["feeding"])
        # Should also infer strong suit in ♦ (since they kept Ace?)
        # Or maybe just feeding signal.
        # The prompt says: "If partner discards high cards to us, infer they're feeding (trust this signal)"
        self.assertIn("feeding", result["signals"])

if __name__ == "__main__":
    unittest.main()
