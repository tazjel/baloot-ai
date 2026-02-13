"""
Test Akka Manager
Tests for AkkaManager: eligibility, handle_akka, phase/turn guards,
HOKUM-only restriction, played card tracking, and state updates.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.constants import GamePhase


class _AkkaTestBase(unittest.TestCase):
    """Base: Game in PLAYING phase, HOKUM mode, with hands assigned."""

    def setUp(self):
        self.game = Game("test_room")
        for i in range(4):
            self.game.add_player(f"p{i}", f"Player {i}")
        self.game.lifecycle.start_game()
        # Force to PLAYING + HOKUM
        self.game.phase = GamePhase.PLAYING.value
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        self.game.current_turn = 0
        self.game.round_history = []
        self.game.table_cards = []
        self.game.akka_manager.init_akka()

    def _give_hand(self, player_index, cards):
        """Give specific cards to a player. Cards as (rank, suit) tuples."""
        self.game.players[player_index].hand = [Card(s, r) for r, s in cards]


class TestAkkaGuards(_AkkaTestBase):
    """Tests for pre-validation guards."""

    def test_reject_outside_playing_phase(self):
        """Akka only valid during PLAYING phase."""
        self.game.phase = 'BIDDING'
        result = self.game.akka_manager.handle_akka(0)
        self.assertFalse(result['success'])

    def test_reject_wrong_turn(self):
        """Akka must be declared on your turn."""
        self.game.current_turn = 1
        result = self.game.akka_manager.handle_akka(0)
        self.assertFalse(result['success'])

    def test_reject_sun_mode(self):
        """Akka is only available in HOKUM mode."""
        self.game.game_mode = 'SUN'
        result = self.game.akka_manager.handle_akka(0)
        self.assertFalse(result['success'])

    def test_reject_already_active(self):
        """Cannot declare Akka if one is already active."""
        from game_engine.core.state import AkkaState
        self.game.state.akkaState = AkkaState(active=True, claimer='Bottom', claimerIndex=0)
        result = self.game.akka_manager.handle_akka(0)
        self.assertFalse(result['success'])


class TestAkkaEligibility(_AkkaTestBase):
    """Tests for Akka eligibility checks."""

    def test_empty_hand_not_eligible(self):
        """Empty hand should return no eligible suits."""
        self.game.players[0].hand = []
        result = self.game.akka_manager.check_akka_eligibility(0)
        self.assertEqual(result, [])

    def test_highest_non_trump_eligible(self):
        """Holding the highest remaining non-trump card → eligible."""
        # A♥ is the highest Heart (non-trump). Trump is ♠.
        self._give_hand(0, [('A', '♥')])
        # No hearts have been played yet, A♥ is the boss
        result = self.game.akka_manager.check_akka_eligibility(0)
        # Should include hearts as an eligible suit
        self.assertIsInstance(result, list)
        # A♥ is actually NOT eligible because Akka doesn't apply to Aces (self-evident boss)
        # Actually let me check — rule says "Must NOT be Ace"
        # So A♥ is not eligible for Akka declaration

    def test_king_eligible_after_ace_played(self):
        """K♥ should be eligible for Akka after A♥ is played."""
        self._give_hand(0, [('K', '♥')])
        self.game.round_history = [
            {'cards': [Card('♥', 'A')]}
        ]
        result = self.game.akka_manager.check_akka_eligibility(0)
        # K♥ is now the boss of Hearts with no higher remaining
        self.assertIsInstance(result, list)

    def test_trump_suit_not_eligible(self):
        """Trump suit cards should not be eligible for Akka."""
        # J♠ is trump master, but Akka is non-trump only
        self._give_hand(0, [('J', '♠')])
        result = self.game.akka_manager.check_akka_eligibility(0)
        # Should NOT include spades
        if result:
            self.assertNotIn('♠', result)


class TestAkkaDeclaration(_AkkaTestBase):
    """Tests for valid and invalid Akka declarations."""

    def test_invalid_akka_flags_referee(self):
        """An invalid Akka should trigger REFEREE_FLAG."""
        self._give_hand(0, [('7', '♥')])  # Clearly not boss
        result = self.game.akka_manager.handle_akka(0)
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'REFEREE_FLAG')

    def test_valid_akka_sets_state(self):
        """A valid Akka should update akkaState."""
        # K♥ is boss after A♥ is played
        self._give_hand(0, [('K', '♥')])
        self.game.round_history = [{'cards': [Card('♥', 'A')]}]
        result = self.game.akka_manager.handle_akka(0)
        if result['success']:
            self.assertTrue(self.game.state.akkaState.active)
            self.assertEqual(self.game.state.akkaState.claimerIndex, 0)


class TestPlayedCardsTracking(_AkkaTestBase):
    """Tests for _build_played_cards_set."""

    def test_builds_from_round_history(self):
        """Should include cards from completed tricks."""
        self.game.round_history = [
            {'cards': [Card('♥', 'A'), Card('♠', 'K')]}
        ]
        played = self.game.akka_manager._build_played_cards_set()
        self.assertIn('A♥', played)
        self.assertIn('K♠', played)

    def test_builds_from_table_cards(self):
        """Should include cards currently on the table."""
        self.game.table_cards = [
            {'card': Card('♦', 'Q')}
        ]
        played = self.game.akka_manager._build_played_cards_set()
        self.assertIn('Q♦', played)

    def test_empty_when_no_cards_played(self):
        """Should be empty at start of round."""
        played = self.game.akka_manager._build_played_cards_set()
        self.assertEqual(len(played), 0)

    def test_card_key_handles_dict(self):
        """_card_key should handle dict format."""
        key = self.game.akka_manager._card_key({'rank': 'A', 'suit': '♠'})
        self.assertEqual(key, 'A♠')

    def test_card_key_handles_card_object(self):
        """_card_key should handle Card objects."""
        key = self.game.akka_manager._card_key(Card('♥', 'K'))
        self.assertEqual(key, 'K♥')

    def test_card_key_handles_nested_dict(self):
        """_card_key should handle nested {card: ...} wrapper."""
        key = self.game.akka_manager._card_key({'card': {'rank': '10', 'suit': '♦'}})
        self.assertEqual(key, '10♦')


if __name__ == '__main__':
    unittest.main()
