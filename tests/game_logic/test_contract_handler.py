"""
Test Contract Handler
Tests for ContractHandler: bidding constraints, turn management, priority,
Ashkal eligibility, Gablak triggering, and round transitions.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.constants import BiddingPhase, BidType


class _BiddingTestBase(unittest.TestCase):
    """Shared setup: creates a 4-player game and starts it."""

    def setUp(self):
        self.game = Game("test_room")
        for i in range(4):
            self.game.add_player(f"p{i}", f"Player {i}")
        self.game.lifecycle.start_game()
        self.engine = self.game.bidding_engine
        self.handler = self.engine._contract
        # Dealer is random; first turn is (dealer+1)%4
        self.first_turn = self.engine.current_turn


class TestBiddingSetup(_BiddingTestBase):
    """Tests for initial bidding state."""

    def test_initial_phase_is_round_1(self):
        """Bidding should start in ROUND_1."""
        self.assertEqual(self.engine.phase, BiddingPhase.ROUND_1)

    def test_priority_queue_starts_left_of_dealer(self):
        """Priority queue starts with player left of dealer (dealer+1)."""
        d = self.engine.dealer_index
        expected_first = (d + 1) % 4
        self.assertEqual(self.engine.priority_queue[0], expected_first)

    def test_dealer_is_last_in_priority(self):
        """Dealer should be last in priority queue."""
        self.assertEqual(self.engine.priority_queue[-1], self.engine.dealer_index)


class TestRound1Constraints(_BiddingTestBase):
    """Tests for Round 1 bidding rules."""

    def test_round1_hokum_must_match_floor_suit(self):
        """In Round 1, Hokum bid must match the floor card suit."""
        floor_suit = self.engine.floor_card.suit
        wrong_suits = [s for s in ['♠', '♥', '♦', '♣'] if s != floor_suit]
        result = self.engine.process_bid(self.first_turn, "HOKUM", suit=wrong_suits[0])
        self.assertIn("error", result)

    def test_round1_hokum_floor_suit_accepted(self):
        """In Round 1, Hokum with floor suit should succeed."""
        floor_suit = self.engine.floor_card.suit
        result = self.engine.process_bid(self.first_turn, "HOKUM", suit=floor_suit)
        self.assertIn("success", result)

    def test_sun_bid_always_valid_round1(self):
        """Sun bid is always valid in Round 1."""
        result = self.engine.process_bid(self.first_turn, "SUN")
        self.assertIn("success", result)


class TestPassMechanics(_BiddingTestBase):
    """Tests for passing during bidding."""

    def test_pass_advances_turn(self):
        """Passing should advance to the next player."""
        turn_before = self.engine.current_turn
        self.engine.process_bid(turn_before, "PASS")
        self.assertEqual(self.engine.current_turn, (turn_before + 1) % 4)

    def test_pass_tracked_in_round_1(self):
        """Passing in round 1 should be tracked."""
        turn = self.engine.current_turn
        self.engine.process_bid(turn, "PASS")
        self.assertIn(turn, self.engine.passed_players_r1)

    def test_all_pass_round1_advances_to_round2(self):
        """All 4 players passing in Round 1 should transition to Round 2."""
        for _ in range(4):
            turn = self.engine.current_turn
            self.engine.process_bid(turn, "PASS")
        self.assertEqual(self.engine.phase, BiddingPhase.ROUND_2)

    def test_all_pass_round2_finishes_bidding(self):
        """All 4 passing in both rounds should finish bidding."""
        # Pass all Round 1
        for _ in range(4):
            self.engine.process_bid(self.engine.current_turn, "PASS")
        # Pass all Round 2
        for _ in range(4):
            self.engine.process_bid(self.engine.current_turn, "PASS")
        self.assertEqual(self.engine.phase, BiddingPhase.FINISHED)


class TestRound2Constraints(_BiddingTestBase):
    """Tests for Round 2 bidding rules."""

    def _go_to_round2(self):
        """Helper: pass all 4 in Round 1 to get to Round 2."""
        for _ in range(4):
            self.engine.process_bid(self.engine.current_turn, "PASS")
        self.assertEqual(self.engine.phase, BiddingPhase.ROUND_2)

    def test_round2_hokum_cannot_use_floor_suit(self):
        """In Round 2, the floor card suit is banned for Hokum."""
        self._go_to_round2()
        floor_suit = self.engine.floor_card.suit
        turn = self.engine.current_turn
        result = self.engine.process_bid(turn, "HOKUM", suit=floor_suit)
        self.assertIn("error", result)

    def test_round2_hokum_other_suit_accepted(self):
        """In Round 2, Hokum with a non-floor suit should succeed."""
        self._go_to_round2()
        floor_suit = self.engine.floor_card.suit
        other_suits = [s for s in ['♠', '♥', '♦', '♣'] if s != floor_suit]
        turn = self.engine.current_turn
        result = self.engine.process_bid(turn, "HOKUM", suit=other_suits[0])
        self.assertIn("success", result)


class TestSunBid(_BiddingTestBase):
    """Tests for Sun bid behavior."""

    def test_sun_finalizes_immediately(self):
        """Sun bid should finalize the auction (advance to DOUBLING)."""
        result = self.engine.process_bid(self.first_turn, "SUN")
        self.assertIn("success", result)
        self.assertTrue(self.engine.is_bidding_complete())

    def test_cannot_bid_hokum_over_sun(self):
        """Cannot bid Hokum once Sun is active."""
        self.engine.process_bid(self.first_turn, "SUN")
        # The engine moves to DOUBLING phase after Sun, so any further bid is treated there
        next_turn = (self.first_turn + 1) % 4
        result = self.engine.process_bid(next_turn, "HOKUM", suit='♠')
        # Should error because Sun is active or bidding is complete
        self.assertIn("error", result)


class TestTurnOrder(_BiddingTestBase):
    """Tests for turn validation."""

    def test_wrong_turn_rejected(self):
        """Bidding out of turn should be rejected."""
        wrong_player = (self.first_turn + 1) % 4  # Not their turn
        result = self.engine.process_bid(wrong_player, "PASS")
        self.assertIn("error", result)


class TestAshkalEligibility(_BiddingTestBase):
    """Tests for Ashkal (partner Sun) eligibility."""

    def test_dealer_is_ashkal_eligible(self):
        """Dealer should be eligible for Ashkal."""
        self.assertTrue(self.handler.is_ashkal_eligible(self.engine.dealer_index))

    def test_left_of_dealer_is_ashkal_eligible(self):
        """Player to the left of dealer should be eligible."""
        left = (self.engine.dealer_index + 3) % 4
        self.assertTrue(self.handler.is_ashkal_eligible(left))

    def test_other_players_not_ashkal_eligible(self):
        """Players across from or right of dealer should NOT be eligible."""
        right = (self.engine.dealer_index + 1) % 4
        across = (self.engine.dealer_index + 2) % 4
        self.assertFalse(self.handler.is_ashkal_eligible(right))
        self.assertFalse(self.handler.is_ashkal_eligible(across))

    def test_ashkal_banned_on_ace_floor(self):
        """Ashkal should be rejected when floor card is an Ace."""
        # Force floor card to Ace
        self.engine.floor_card = Card('♠', 'A')
        dealer = self.engine.dealer_index
        # Move turn to dealer
        self.engine.current_turn = dealer
        result = self.engine.process_bid(dealer, "ASHKAL")
        self.assertIn("error", result)


class TestContractState(_BiddingTestBase):
    """Tests for contract state tracking."""

    def test_hokum_sets_contract_type(self):
        """After a Hokum bid, contract type should be HOKUM."""
        floor_suit = self.engine.floor_card.suit
        self.engine.process_bid(self.first_turn, "HOKUM", suit=floor_suit)
        self.assertEqual(self.engine.contract.type, BidType.HOKUM)

    def test_hokum_sets_contract_suit(self):
        """After a Hokum bid, contract suit should match."""
        floor_suit = self.engine.floor_card.suit
        self.engine.process_bid(self.first_turn, "HOKUM", suit=floor_suit)
        self.assertEqual(self.engine.contract.suit, floor_suit)

    def test_sun_sets_contract_type(self):
        """After a Sun bid, contract type should be SUN."""
        self.engine.process_bid(self.first_turn, "SUN")
        self.assertEqual(self.engine.contract.type, BidType.SUN)

    def test_contract_round_tracked(self):
        """Contract should track which round the bid occurred in."""
        floor_suit = self.engine.floor_card.suit
        self.engine.process_bid(self.first_turn, "HOKUM", suit=floor_suit)
        self.assertEqual(self.engine.contract.round, 1)


class TestBiddingComplete(_BiddingTestBase):
    """Tests for is_bidding_complete."""

    def test_not_complete_during_round_1(self):
        """Bidding should not be complete during Round 1."""
        self.assertFalse(self.engine.is_bidding_complete())

    def test_complete_after_sun(self):
        """Bidding should be complete after a Sun bid."""
        self.engine.process_bid(self.first_turn, "SUN")
        self.assertTrue(self.engine.is_bidding_complete())

    def test_complete_after_all_pass(self):
        """Bidding should be complete after all players pass both rounds."""
        for _ in range(4):
            self.engine.process_bid(self.engine.current_turn, "PASS")
        for _ in range(4):
            self.engine.process_bid(self.engine.current_turn, "PASS")
        self.assertTrue(self.engine.is_bidding_complete())


if __name__ == '__main__':
    unittest.main()
