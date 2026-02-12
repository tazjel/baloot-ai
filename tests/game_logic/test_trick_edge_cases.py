"""
Test Trick Manager Edge Cases
Tests for trump overtrump, partner winning, void suit, and trick winner determination.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, POINT_VALUES_SUN, POINT_VALUES_HOKUM


class TestTrickWinner(unittest.TestCase):
    """Tests for TrickManager.get_trick_winner in various scenarios."""

    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p1", "Player 1")  # Index 0, Bottom, US
        self.game.add_player("p2", "Player 2")  # Index 1, Right, THEM
        self.game.add_player("p3", "Player 3")  # Index 2, Top, US
        self.game.add_player("p4", "Player 4")  # Index 3, Left, THEM

    def _set_hokum(self, trump_suit='♠'):
        """Set up a Hokum game with the given trump suit."""
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = trump_suit
        self.game.phase = 'PLAYING'

    def _set_sun(self):
        """Set up a Sun (no-trump) game."""
        self.game.game_mode = 'SUN'
        self.game.trump_suit = None
        self.game.phase = 'PLAYING'

    def _play_cards(self, cards_with_positions):
        """Simulate playing cards to the table.
        cards_with_positions: list of (Card, position_str) tuples
        """
        self.game.table_cards = [
            {'card': card, 'playedBy': pos}
            for card, pos in cards_with_positions
        ]

    # ---------- HOKUM (Trump) Tests ----------

    def test_trump_beats_lead_suit(self):
        """A trump card should beat any non-trump card, even a high one."""
        self._set_hokum(trump_suit='♠')
        self._play_cards([
            (Card('♥', 'A'), 'Bottom'),  # Lead: Ace of Hearts
            (Card('♠', '7'), 'Right'),   # Trump 7 — lowest trump
            (Card('♥', 'K'), 'Top'),     # King of Hearts
            (Card('♥', '10'), 'Left'),   # 10 of Hearts
        ])
        winner_idx = self.game.trick_manager.get_trick_winner()
        self.assertEqual(winner_idx, 1, "Lowest trump (♠7) should beat Ace of lead suit")

    def test_trump_overtrump(self):
        """A higher trump should beat a lower trump (overtrump)."""
        self._set_hokum(trump_suit='♠')
        self._play_cards([
            (Card('♥', 'A'), 'Bottom'),  # Lead: Ace of Hearts
            (Card('♠', '7'), 'Right'),   # Low trump
            (Card('♥', 'K'), 'Top'),     # Follows suit
            (Card('♠', '9'), 'Left'),    # Higher trump (9 is very strong in Hokum)
        ])
        winner_idx = self.game.trick_manager.get_trick_winner()
        self.assertEqual(winner_idx, 3, "♠9 should overtrump ♠7 (Hokum order: 9 > 7)")

    def test_trump_jack_beats_all(self):
        """Jack of trump is the highest card in Hokum — should always win."""
        self._set_hokum(trump_suit='♠')
        self._play_cards([
            (Card('♥', 'A'), 'Bottom'),  # Lead
            (Card('♠', '9'), 'Right'),   # Strong trump (9)
            (Card('♠', 'A'), 'Top'),     # Trump Ace
            (Card('♠', 'J'), 'Left'),    # Trump Jack — highest!
        ])
        winner_idx = self.game.trick_manager.get_trick_winner()
        self.assertEqual(winner_idx, 3, "Trump Jack should beat Trump 9 and Trump Ace in Hokum")

    def test_no_trump_played_highest_lead_wins(self):
        """If nobody plays trump, highest card of the lead suit wins."""
        self._set_hokum(trump_suit='♠')
        self._play_cards([
            (Card('♥', '8'), 'Bottom'),  # Lead: Hearts
            (Card('♥', 'A'), 'Right'),   # Highest Heart
            (Card('♥', 'Q'), 'Top'),
            (Card('♦', 'A'), 'Left'),    # Off-suit Ace — doesn't count
        ])
        winner_idx = self.game.trick_manager.get_trick_winner()
        self.assertEqual(winner_idx, 1, "Ace of lead suit should win when no trump is played")

    def test_off_suit_card_loses(self):
        """Off-suit non-trump card should never win, even if it's high."""
        self._set_hokum(trump_suit='♠')
        self._play_cards([
            (Card('♥', '7'), 'Bottom'),  # Lead: low Heart
            (Card('♦', 'A'), 'Right'),   # Off-suit Ace
            (Card('♣', 'A'), 'Top'),     # Off-suit Ace
            (Card('♥', '8'), 'Left'),    # Low Heart but follows suit
        ])
        winner_idx = self.game.trick_manager.get_trick_winner()
        self.assertEqual(winner_idx, 3, "♥8 follows suit and beats ♥7; off-suit As don't count")

    # ---------- SUN (No-Trump) Tests ----------

    def test_sun_highest_lead_suit_wins(self):
        """In Sun mode, only cards matching the lead suit compete."""
        self._set_sun()
        self._play_cards([
            (Card('♦', 'Q'), 'Bottom'),  # Lead: Queen of Diamonds
            (Card('♦', 'A'), 'Right'),   # Ace of Diamonds — highest
            (Card('♠', 'A'), 'Top'),     # Off-suit Ace, doesn't count
            (Card('♦', '10'), 'Left'),   # 10 of Diamonds
        ])
        winner_idx = self.game.trick_manager.get_trick_winner()
        self.assertEqual(winner_idx, 1, "Ace of lead suit wins in Sun mode")

    def test_sun_off_suit_never_wins(self):
        """In Sun mode, off-suit cards can never win regardless of rank."""
        self._set_sun()
        self._play_cards([
            (Card('♣', '7'), 'Bottom'),  # Lead: lowest Club
            (Card('♠', 'A'), 'Right'),   # Off-suit Ace
            (Card('♥', 'A'), 'Top'),     # Off-suit Ace
            (Card('♦', 'A'), 'Left'),    # Off-suit Ace
        ])
        winner_idx = self.game.trick_manager.get_trick_winner()
        self.assertEqual(winner_idx, 0, "Lead card wins if nobody follows suit in Sun")

    def test_sun_10_beats_king(self):
        """In Sun, 10 ranks higher than K (ORDER_SUN: 7,8,9,J,Q,K,10,A)."""
        self._set_sun()
        self._play_cards([
            (Card('♥', 'K'), 'Bottom'),  # Lead: King
            (Card('♥', '10'), 'Right'),  # 10 outranks K in Sun
            (Card('♥', '9'), 'Top'),
            (Card('♥', '8'), 'Left'),
        ])
        winner_idx = self.game.trick_manager.get_trick_winner()
        self.assertEqual(winner_idx, 1, "10 should beat K in Sun order")


class TestCanBeatTrump(unittest.TestCase):
    """Tests for TrickManager.can_beat_trump — checking if hand can overtrump."""

    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p1", "Player 1")
        self.game.add_player("p2", "Player 2")
        self.game.add_player("p3", "Player 3")
        self.game.add_player("p4", "Player 4")
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'

    def test_can_beat_with_higher_trump(self):
        """Hand with a higher trump can beat the winning trump card."""
        winning_card = Card('♠', '8')
        hand = [Card('♥', 'A'), Card('♠', '9'), Card('♦', 'K')]
        can_beat, cards = self.game.trick_manager.can_beat_trump(winning_card, hand)
        self.assertTrue(can_beat)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].rank, '9')

    def test_cannot_beat_trump_jack(self):
        """No trump card can beat the Jack of trump — it's the highest."""
        winning_card = Card('♠', 'J')
        hand = [Card('♠', '9'), Card('♠', 'A'), Card('♠', '10')]
        can_beat, cards = self.game.trick_manager.can_beat_trump(winning_card, hand)
        self.assertFalse(can_beat)
        self.assertEqual(len(cards), 0)

    def test_multiple_beating_trumps(self):
        """Hand with multiple higher trumps should return all of them."""
        winning_card = Card('♠', '8')
        hand = [Card('♠', '9'), Card('♠', 'J'), Card('♠', 'A')]
        can_beat, cards = self.game.trick_manager.can_beat_trump(winning_card, hand)
        self.assertTrue(can_beat)
        self.assertTrue(len(cards) >= 2, "Should find multiple cards that can beat ♠8")

    def test_no_trump_in_hand(self):
        """Hand with no trump cards at all."""
        winning_card = Card('♠', '7')
        hand = [Card('♥', 'A'), Card('♦', 'K'), Card('♣', 'J')]
        can_beat, cards = self.game.trick_manager.can_beat_trump(winning_card, hand)
        self.assertFalse(can_beat)
        self.assertEqual(len(cards), 0)


class TestCardPoints(unittest.TestCase):
    """Tests for TrickManager.get_card_points in both modes."""

    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p1", "Player 1")
        self.game.add_player("p2", "Player 2")
        self.game.add_player("p3", "Player 3")
        self.game.add_player("p4", "Player 4")

    def test_sun_point_values(self):
        """Verify point values in Sun mode."""
        self.game.game_mode = 'SUN'
        tm = self.game.trick_manager
        self.assertEqual(tm.get_card_points(Card('♥', '7')), 0)
        self.assertEqual(tm.get_card_points(Card('♥', 'J')), 2)
        self.assertEqual(tm.get_card_points(Card('♥', 'Q')), 3)
        self.assertEqual(tm.get_card_points(Card('♥', 'K')), 4)
        self.assertEqual(tm.get_card_points(Card('♥', '10')), 10)
        self.assertEqual(tm.get_card_points(Card('♥', 'A')), 11)

    def test_hokum_trump_card_points(self):
        """Trump cards in Hokum get Hokum point values (9=14, J=20)."""
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        tm = self.game.trick_manager
        self.assertEqual(tm.get_card_points(Card('♠', '9')), 14)
        self.assertEqual(tm.get_card_points(Card('♠', 'J')), 20)
        self.assertEqual(tm.get_card_points(Card('♠', 'A')), 11)

    def test_hokum_nontrump_card_uses_sun_values(self):
        """Non-trump cards in Hokum use Sun point values."""
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        tm = self.game.trick_manager
        # Hearts (non-trump) should use Sun values
        self.assertEqual(tm.get_card_points(Card('♥', '9')), 0)
        self.assertEqual(tm.get_card_points(Card('♥', 'J')), 2)
        self.assertEqual(tm.get_card_points(Card('♥', 'A')), 11)


if __name__ == '__main__':
    unittest.main()
