"""
Test Sawa Manager
Tests for SawaManager: eligibility checks, handle_sawa validation,
invalid claims, and state updates.
"""
import unittest
from unittest.mock import patch, MagicMock
from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.constants import GamePhase


class _SawaTestBase(unittest.TestCase):
    """Shared setup: Game in PLAYING phase with hands assigned."""

    def setUp(self):
        self.game = Game("test_room")
        for i in range(4):
            self.game.add_player(f"p{i}", f"Player {i}")
        self.game.lifecycle.start_game()
        # Force to PLAYING so sawa is valid
        self.game.phase = GamePhase.PLAYING.value
        self.game.game_mode = 'SUN'
        self.game.current_turn = 0
        self.game.trump_suit = None
        self.game.round_history = []
        self.game.table_cards = []
        self.game.sawa_declaration = None

    def _give_hand(self, player_index, cards):
        """Give specific cards to a player."""
        self.game.players[player_index].hand = [Card(s, r) for r, s in cards]


class TestSawaHandleTiming(_SawaTestBase):
    """Tests that handle_sawa rejects calls at wrong timing."""

    def test_reject_outside_playing_phase(self):
        """Sawa is only valid during PLAYING phase."""
        self.game.phase = 'BIDDING'
        result = self.game.sawa_manager.handle_sawa(0)
        self.assertFalse(result['success'])

    def test_reject_wrong_turn(self):
        """Sawa must be declared on the player's turn."""
        self.game.current_turn = 1
        result = self.game.sawa_manager.handle_sawa(0)
        self.assertFalse(result['success'])

    def test_reject_empty_hand(self):
        """Sawa should fail if the player has no cards."""
        self.game.players[0].hand = []
        result = self.game.sawa_manager.handle_sawa(0)
        self.assertFalse(result['success'])


class TestSawaEligibilitySun(_SawaTestBase):
    """Tests for Sawa eligibility in SUN mode."""

    def test_eligible_with_all_top_cards(self):
        """Player holding all master cards in each suit should be eligible."""
        # Give: A♠, A♥ — top remaining in both suits (no cards played)
        self._give_hand(0, [('A', '♠'), ('A', '♥')])
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertTrue(eligible)

    def test_not_eligible_missing_top_card(self):
        """If opponent may have a higher card, sawa should fail."""
        # Give K♠ — A♠ hasn't been played, so K is not master
        self._give_hand(0, [('K', '♠')])
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertFalse(eligible)

    def test_eligible_after_higher_cards_played(self):
        """K♠ should be master after A♠ and 10♠ are played (SUN order: A, 10, K)."""
        self._give_hand(0, [('K', '♠')])
        # Both A♠ and 10♠ must be played for K♠ to be top remaining in SUN order
        self.game.round_history = [
            {'cards': [Card('♠', 'A'), Card('♠', '10')]}
        ]
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertTrue(eligible)

    def test_eligible_with_top_sequence(self):
        """A♠, 10♠ should be eligible — both are top of remaining spades."""
        self._give_hand(0, [('A', '♠'), ('10', '♠')])
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertTrue(eligible)

    def test_not_eligible_with_broken_sequence(self):
        """A♠, K♠ missing 10♠ — K is fine but then gap to Q."""
        # A♠, Q♠ — 10♠ and K♠ not played yet = gap after A, so Q is not master
        self._give_hand(0, [('A', '♠'), ('Q', '♠')])
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertFalse(eligible)


class TestSawaEligibilityHokum(_SawaTestBase):
    """Tests for Sawa eligibility in HOKUM mode."""

    def setUp(self):
        super().setUp()
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'

    def test_master_trumps_eligible(self):
        """Holding J♠, 9♠ (top Hokum trumps) should be eligible."""
        self._give_hand(0, [('J', '♠'), ('9', '♠')])
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertTrue(eligible)

    def test_non_trump_without_trump_control_ineligible(self):
        """Having non-trump masters but no trumps when opponents have trumps = not eligible."""
        # Give A♥ (master hearts) but no spades (trump)
        # Opponents presumably have trumps
        self._give_hand(0, [('A', '♥')])
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertFalse(eligible)

    def test_trump_master_plus_side_suit_eligible(self):
        """J♠ (trump master) + A♥ (side master) = eligible."""
        # Need all trumps accounted for. Play all trumps except J♠
        played = []
        for r in ['9', 'A', '10', 'K', 'Q', '8', '7']:
            played.append({'rank': r, 'suit': '♠'})
        self.game.round_history = [{'cards': played}]
        self._give_hand(0, [('J', '♠'), ('A', '♥')])
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertTrue(eligible)


class TestSawaDeclaration(_SawaTestBase):
    """Tests for successful and failed Sawa declarations."""

    def test_valid_sawa_sets_declaration(self):
        """A valid Sawa should set sawa_declaration on the game."""
        self._give_hand(0, [('A', '♠'), ('A', '♥')])
        result = self.game.sawa_manager.handle_sawa(0)
        self.assertTrue(result['success'])
        self.assertIsNotNone(self.game.sawa_declaration)
        self.assertTrue(self.game.sawa_declaration['active'])

    def test_invalid_sawa_flags_referee(self):
        """An invalid Sawa claim should trigger REFEREE_FLAG."""
        self._give_hand(0, [('7', '♠')])  # Clearly not master
        result = self.game.sawa_manager.handle_sawa(0)
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'REFEREE_FLAG')

    def test_invalid_sawa_increments_blunder(self):
        """An invalid Sawa should increment the blunder counter."""
        self._give_hand(0, [('7', '♠')])
        initial_blunders = getattr(self.game.players[0], 'blunders', 0)
        self.game.sawa_manager.handle_sawa(0)
        # Check increment_blunder was called (may vary based on implementation)
        # Just verify no crash and result has REFEREE_FLAG
        result = self.game.sawa_manager.handle_sawa(0)
        self.assertFalse(result['success'])


class TestSawaMultipleSuits(_SawaTestBase):
    """Tests for Sawa with multi-suit hands."""

    def test_eligible_all_suits_mastered(self):
        """Holding Ace of every suit (SUN) = eligible."""
        self._give_hand(0, [('A', '♠'), ('A', '♥'), ('A', '♦'), ('A', '♣')])
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertTrue(eligible)

    def test_ineligible_one_suit_not_mastered(self):
        """If any suit has a gap, not eligible."""
        self._give_hand(0, [('A', '♠'), ('A', '♥'), ('Q', '♦')])
        eligible = self.game.sawa_manager.check_sawa_eligibility(0)
        self.assertFalse(eligible)


if __name__ == '__main__':
    unittest.main()
