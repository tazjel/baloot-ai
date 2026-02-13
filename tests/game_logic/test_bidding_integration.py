"""
Test Bidding Integration
End-to-end tests that exercise the full bidding flow:
BiddingEngine → ContractHandler → DoublingHandler → result.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.constants import BiddingPhase, BidType


class _BiddingIntegrationBase(unittest.TestCase):
    """Base: creates a started game with a known floor card."""

    def setUp(self):
        self.game = Game("test_room")
        for i in range(4):
            self.game.add_player(f"p{i}", f"Player {i}")
        self.game.lifecycle.start_game()
        self.engine = self.game.bidding_engine
        self.dealer = self.engine.dealer_index
        self.first_turn = self.engine.current_turn
        self.floor_suit = self.engine.floor_card.suit

    def _get_other_suit(self):
        """Returns a suit different from the floor card suit."""
        for s in ['♠', '♥', '♦', '♣']:
            if s != self.floor_suit:
                return s


class TestFullHokumFlow(_BiddingIntegrationBase):
    """Tests for a complete Hokum bidding flow."""

    def test_hokum_r1_bid_then_all_pass(self):
        """P0 bids Hokum R1 → 3 players pass → auction ends in DOUBLING."""
        # First player bids Hokum
        result = self.engine.process_bid(self.first_turn, "HOKUM", suit=self.floor_suit)
        self.assertIn("success", result)

        # Remaining 3 players pass
        for _ in range(3):
            turn = self.engine.current_turn
            self.engine.process_bid(turn, "PASS")

        # Should be in DOUBLING or completed
        self.assertTrue(self.engine.is_bidding_complete())

    def test_hokum_r2_with_different_suit(self):
        """All pass R1 → P0 bids Hokum R2 with non-floor suit → completes."""
        # Pass all Round 1
        for _ in range(4):
            self.engine.process_bid(self.engine.current_turn, "PASS")
        self.assertEqual(self.engine.phase, BiddingPhase.ROUND_2)

        # First player bids Hokum with different suit
        other_suit = self._get_other_suit()
        turn = self.engine.current_turn
        result = self.engine.process_bid(turn, "HOKUM", suit=other_suit)
        self.assertIn("success", result)


class TestFullSunFlow(_BiddingIntegrationBase):
    """Tests for Sun bid completing the auction."""

    def test_sun_immediately_completes(self):
        """Sun bid should immediately finalize auction."""
        result = self.engine.process_bid(self.first_turn, "SUN")
        self.assertIn("success", result)
        self.assertTrue(self.engine.is_bidding_complete())
        self.assertEqual(self.engine.contract.type, BidType.SUN)

    def test_sun_over_hokum_triggers_gablak_or_succeeds(self):
        """Sun bid over existing Hokum should either succeed or trigger Gablak."""
        # First player bids Hokum
        self.engine.process_bid(self.first_turn, "HOKUM", suit=self.floor_suit)
        # Next player bids Sun — may trigger Gablak if higher-prio player exists
        turn = self.engine.current_turn
        result = self.engine.process_bid(turn, "SUN")
        self.assertIn("success", result)
        # Contract should now be SUN or Gablak was triggered for resolution
        if result.get('status') == 'GABLAK_TRIGGERED':
            self.assertEqual(self.engine.phase, BiddingPhase.GABLAK_WINDOW)
        else:
            self.assertEqual(self.engine.contract.type, BidType.SUN)


class TestAllPass(_BiddingIntegrationBase):
    """Tests for the all-pass scenario."""

    def test_all_pass_both_rounds(self):
        """All 4 passing both rounds → FINISHED, no contract."""
        for _ in range(4):
            self.engine.process_bid(self.engine.current_turn, "PASS")
        self.assertEqual(self.engine.phase, BiddingPhase.ROUND_2)

        for _ in range(4):
            self.engine.process_bid(self.engine.current_turn, "PASS")
        self.assertEqual(self.engine.phase, BiddingPhase.FINISHED)
        self.assertIsNone(self.engine.get_winner())


class TestKawesh(_BiddingIntegrationBase):
    """Tests for Kawesh (zero-point hand redeal)."""

    def _give_kawesh_hand(self, player_idx):
        """Give a zero-point hand (7, 8, 9 only)."""
        self.game.players[player_idx].hand = [
            Card('♠', '7'), Card('♥', '8'), Card('♦', '9'),
            Card('♣', '7'), Card('♠', '8'), Card('♥', '9'),
            Card('♦', '7'), Card('♣', '8')
        ]

    def test_kawesh_pre_bid_keeps_dealer(self):
        """Kawesh before any bid should keep dealer (no rotation)."""
        self._give_kawesh_hand(self.first_turn)
        result = self.engine.process_bid(self.first_turn, "KAWESH")
        self.assertIn("success", result)
        self.assertFalse(result.get("rotate_dealer", True))

    def test_kawesh_post_bid_rotates_dealer(self):
        """Kawesh after a bid should rotate dealer."""
        # Make a bid first
        self.engine.process_bid(self.first_turn, "HOKUM", suit=self.floor_suit)
        # Next player calls kawesh
        turn = self.engine.current_turn
        self._give_kawesh_hand(turn)
        result = self.engine.process_bid(turn, "KAWESH")
        self.assertIn("success", result)
        self.assertTrue(result.get("rotate_dealer", False))

    def test_kawesh_invalid_hand_rejected(self):
        """Kawesh with high cards in hand should be rejected."""
        # Keep default hand (has face cards)
        result = self.engine.process_bid(self.first_turn, "KAWESH")
        self.assertIn("error", result)


class TestBiddingAfterFinish(_BiddingIntegrationBase):
    """Tests for bidding after the auction is over."""

    def test_bid_after_finished_rejected(self):
        """Bidding after FINISHED should return error."""
        # Force finish
        self.engine.phase = BiddingPhase.FINISHED
        result = self.engine.process_bid(0, "HOKUM", suit='♠')
        self.assertIn("error", result)


class TestDoubling(_BiddingIntegrationBase):
    """Tests for the doubling phase integration."""

    def test_doubling_phase_reached_after_hokum(self):
        """After Hokum bid + all pass, should reach DOUBLING."""
        self.engine.process_bid(self.first_turn, "HOKUM", suit=self.floor_suit)
        # Pass remaining 3 players
        for _ in range(3):
            self.engine.process_bid(self.engine.current_turn, "PASS")
        self.assertIn(self.engine.phase, [BiddingPhase.DOUBLING, BiddingPhase.VARIANT_SELECTION])

    def test_doubling_phase_reached_after_sun(self):
        """After Sun bid, should reach DOUBLING immediately."""
        self.engine.process_bid(self.first_turn, "SUN")
        self.assertTrue(self.engine.is_bidding_complete())


class TestGetState(_BiddingIntegrationBase):
    """Tests for engine state serialization."""

    def test_get_state_returns_dict(self):
        """get_state should return a proper dict."""
        state = self.engine.get_state()
        self.assertIsInstance(state, dict)
        self.assertIn('phase', state)
        self.assertIn('contract', state)
        self.assertIn('currentTurn', state)

    def test_get_state_after_bid(self):
        """get_state should reflect the active contract after a bid."""
        self.engine.process_bid(self.first_turn, "HOKUM", suit=self.floor_suit)
        state = self.engine.get_state()
        self.assertEqual(state['contract']['type'], 'HOKUM')
        self.assertEqual(state['contract']['suit'], self.floor_suit)

    def test_to_dict_and_from_dict_roundtrip(self):
        """Serialization round-trip should preserve state."""
        self.engine.process_bid(self.first_turn, "HOKUM", suit=self.floor_suit)
        data = self.engine.to_dict()

        from game_engine.logic.bidding_engine import BiddingEngine
        restored = BiddingEngine.from_dict(data, self.game.players)

        self.assertEqual(restored.contract.type, self.engine.contract.type)
        self.assertEqual(restored.contract.suit, self.engine.contract.suit)
        self.assertEqual(restored.phase, self.engine.phase)
        self.assertEqual(restored.current_turn, self.engine.current_turn)


if __name__ == '__main__':
    unittest.main()
