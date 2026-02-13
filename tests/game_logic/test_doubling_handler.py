"""
Test Doubling Handler
Tests for DoublingHandler: doubling chain (Double → Triple → Four → Gahwa),
team restrictions, Sun Firewall, variant selection, and phase transitions.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.models.constants import BiddingPhase, BidType


class _DoublingTestBase(unittest.TestCase):
    """Base: creates a game that has completed the auction phase."""

    def setUp(self):
        self.game = Game("test_room")
        for i in range(4):
            self.game.add_player(f"p{i}", f"Player {i}")
        self.game.lifecycle.start_game()
        self.engine = self.game.bidding_engine

        # Bid Hokum to get a contract
        self.first_turn = self.engine.current_turn
        floor_suit = self.engine.floor_card.suit
        self.engine.process_bid(self.first_turn, "HOKUM", suit=floor_suit)

        # Pass remaining 3 to get to DOUBLING
        for _ in range(3):
            self.engine.process_bid(self.engine.current_turn, "PASS")

        self.bidder_idx = self.engine.contract.bidder_idx
        self.bidder_team = self.game.players[self.bidder_idx].team

    def _get_opponent_idx(self):
        """Get an opponent player index."""
        for p in self.game.players:
            if p.team != self.bidder_team:
                return p.index
        return None

    def _get_teammate_idx(self):
        """Get the bidder's teammate index."""
        for p in self.game.players:
            if p.team == self.bidder_team and p.index != self.bidder_idx:
                return p.index
        return None


class TestDoublingPhaseEntry(_DoublingTestBase):
    """Tests for entering the doubling phase."""

    def test_phase_is_doubling(self):
        """After auction, phase should be DOUBLING."""
        self.assertEqual(self.engine.phase, BiddingPhase.DOUBLING)

    def test_first_turn_is_left_of_bidder(self):
        """Doubling starts with player left of bidder."""
        expected = (self.bidder_idx + 1) % 4
        self.assertEqual(self.engine.current_turn, expected)


class TestDoubleAction(_DoublingTestBase):
    """Tests for the DOUBLE action."""

    def test_opponent_can_double(self):
        """Opponent should be able to double."""
        opp = self._get_opponent_idx()
        self.engine.current_turn = opp
        result = self.engine.process_bid(opp, "DOUBLE")
        self.assertIn("success", result)
        self.assertEqual(self.engine.contract.level, 2)

    def test_bidder_team_cannot_double(self):
        """Bidder's team cannot double their own bid."""
        teammate = self._get_teammate_idx()
        self.engine.current_turn = teammate
        result = self.engine.process_bid(teammate, "DOUBLE")
        self.assertIn("error", result)

    def test_cannot_double_twice(self):
        """Cannot double if already doubled."""
        opp = self._get_opponent_idx()
        self.engine.current_turn = opp
        self.engine.process_bid(opp, "DOUBLE")
        # Try doubling again
        result = self.engine.process_bid(opp, "DOUBLE")
        self.assertIn("error", result)


class TestTripleAction(_DoublingTestBase):
    """Tests for the TRIPLE action."""

    def test_bidder_team_can_triple_after_double(self):
        """Bidder team can triple after opponent doubles."""
        opp = self._get_opponent_idx()
        self.engine.current_turn = opp
        self.engine.process_bid(opp, "DOUBLE")

        teammate = self._get_teammate_idx()
        self.engine.current_turn = teammate
        result = self.engine.process_bid(teammate, "TRIPLE")
        self.assertIn("success", result)
        self.assertEqual(self.engine.contract.level, 3)

    def test_cannot_triple_without_double(self):
        """Cannot triple if not doubled first."""
        teammate = self._get_teammate_idx()
        self.engine.current_turn = teammate
        result = self.engine.process_bid(teammate, "TRIPLE")
        self.assertIn("error", result)

    def test_opponent_cannot_triple(self):
        """Opponents cannot triple (only bidder team can)."""
        opp = self._get_opponent_idx()
        self.engine.current_turn = opp
        self.engine.process_bid(opp, "DOUBLE")
        # Opponent tries to triple
        result = self.engine.process_bid(opp, "TRIPLE")
        self.assertIn("error", result)


class TestFourAndGahwa(_DoublingTestBase):
    """Tests for FOUR and GAHWA actions."""

    def _setup_chain(self):
        """Setup: Double → Triple."""
        opp = self._get_opponent_idx()
        teammate = self._get_teammate_idx()
        self.engine.current_turn = opp
        self.engine.process_bid(opp, "DOUBLE")
        self.engine.current_turn = teammate
        self.engine.process_bid(teammate, "TRIPLE")
        return opp, teammate

    def test_opponent_can_four_after_triple(self):
        """Opponent can Four after bidder team triples."""
        opp, _ = self._setup_chain()
        self.engine.current_turn = opp
        result = self.engine.process_bid(opp, "FOUR")
        self.assertIn("success", result)
        self.assertEqual(self.engine.contract.level, 4)

    def test_bidder_team_can_gahwa_after_four(self):
        """Bidder team can Gahwa after opponent fours."""
        opp, teammate = self._setup_chain()
        self.engine.current_turn = opp
        self.engine.process_bid(opp, "FOUR")
        self.engine.current_turn = teammate
        result = self.engine.process_bid(teammate, "GAHWA")
        self.assertIn("success", result)
        self.assertEqual(self.engine.contract.level, 100)

    def test_cannot_four_without_triple(self):
        """Cannot Four if not tripled first."""
        opp = self._get_opponent_idx()
        self.engine.current_turn = opp
        self.engine.process_bid(opp, "DOUBLE")
        result = self.engine.process_bid(opp, "FOUR")
        self.assertIn("error", result)

    def test_cannot_gahwa_without_four(self):
        """Cannot Gahwa if not foured first."""
        opp, teammate = self._setup_chain()
        self.engine.current_turn = teammate
        result = self.engine.process_bid(teammate, "GAHWA")
        self.assertIn("error", result)


class TestPassInDoubling(_DoublingTestBase):
    """Tests for PASS during doubling."""

    def test_pass_hokum_goes_to_variant_selection(self):
        """Passing in Hokum doubling should go to VARIANT_SELECTION."""
        opp = self._get_opponent_idx()
        self.engine.current_turn = opp
        result = self.engine.process_bid(opp, "PASS")
        self.assertEqual(self.engine.phase, BiddingPhase.VARIANT_SELECTION)

    def test_pass_sun_goes_to_finished(self):
        """Passing in Sun doubling should go to FINISHED."""
        # Need to set up a Sun game instead
        game2 = Game("test2")
        for i in range(4):
            game2.add_player(f"p{i}", f"Player {i}")
        game2.lifecycle.start_game()
        eng = game2.bidding_engine
        first = eng.current_turn
        eng.process_bid(first, "SUN")
        # Now in DOUBLING for Sun
        opp_idx = None
        bidder_team = game2.players[eng.contract.bidder_idx].team
        for p in game2.players:
            if p.team != bidder_team:
                opp_idx = p.index
                break
        eng.current_turn = opp_idx
        result = eng.process_bid(opp_idx, "PASS")
        self.assertEqual(eng.phase, BiddingPhase.FINISHED)


class TestVariantSelection(_DoublingTestBase):
    """Tests for OPEN/CLOSED variant selection in Hokum."""

    def _goto_variant(self):
        """Pass through doubling to reach VARIANT_SELECTION."""
        opp = self._get_opponent_idx()
        self.engine.current_turn = opp
        self.engine.process_bid(opp, "PASS")
        self.assertEqual(self.engine.phase, BiddingPhase.VARIANT_SELECTION)

    def test_bidder_can_select_open(self):
        """Bidder should be able to select OPEN."""
        self._goto_variant()
        result = self.engine.process_bid(self.bidder_idx, "OPEN")
        self.assertIn("success", result)
        self.assertEqual(self.engine.contract.variant, "OPEN")
        self.assertEqual(self.engine.phase, BiddingPhase.FINISHED)

    def test_bidder_can_select_closed(self):
        """Bidder should be able to select CLOSED."""
        self._goto_variant()
        result = self.engine.process_bid(self.bidder_idx, "CLOSED")
        self.assertIn("success", result)
        self.assertEqual(self.engine.contract.variant, "CLOSED")

    def test_non_bidder_cannot_select_variant(self):
        """Only the bidder can choose the variant."""
        self._goto_variant()
        opp = self._get_opponent_idx()
        result = self.engine.process_bid(opp, "OPEN")
        self.assertIn("error", result)

    def test_invalid_variant_rejected(self):
        """Invalid variant name should be rejected."""
        self._goto_variant()
        result = self.engine.process_bid(self.bidder_idx, "HALF_OPEN")
        self.assertIn("error", result)


class TestUnknownAction(_DoublingTestBase):
    """Tests for unknown doubling actions."""

    def test_unknown_action_rejected(self):
        """Unknown action should return error."""
        opp = self._get_opponent_idx()
        self.engine.current_turn = opp
        result = self.engine.process_bid(opp, "MEGA_DOUBLE")
        self.assertIn("error", result)


if __name__ == '__main__':
    unittest.main()
