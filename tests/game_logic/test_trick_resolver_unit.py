"""
Test Trick Resolver (Unit)
Tests for TrickResolver static methods: get_card_points, get_trick_winner, can_beat_trump.
These are pure functions with no state — ideal for unit testing.
"""
import unittest
from game_engine.logic.trick_resolver import TrickResolver
from game_engine.models.card import Card


class TestGetCardPoints(unittest.TestCase):
    """Tests for TrickResolver.get_card_points."""

    def test_ace_hokum_trump(self):
        """Ace of trump suit should be 11 points in HOKUM."""
        card = Card('♠', 'A')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 11)

    def test_ace_hokum_non_trump(self):
        """Ace of non-trump suit should also be 11 points."""
        card = Card('♥', 'A')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 11)

    def test_ten_is_10_points(self):
        """10 should be 10 points in any mode."""
        card = Card('♠', '10')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 10)

    def test_king_is_4_points(self):
        """King should be 4 points."""
        card = Card('♠', 'K')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 4)

    def test_queen_is_3_points(self):
        """Queen should be 3 points."""
        card = Card('♥', 'Q')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 3)

    def test_jack_non_trump_is_2_points(self):
        """Jack of non-trump should be 2 points in HOKUM."""
        card = Card('♥', 'J')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 2)

    def test_jack_trump_is_20_points(self):
        """Jack of trump suit should be 20 points in HOKUM."""
        card = Card('♠', 'J')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 20)

    def test_nine_trump_is_14_points(self):
        """9 of trump suit should be 14 points in HOKUM."""
        card = Card('♠', '9')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 14)

    def test_nine_non_trump_is_0_points(self):
        """9 of non-trump should be 0 points in HOKUM."""
        card = Card('♥', '9')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 0)

    def test_seven_is_0_points(self):
        """7 should be 0 points."""
        card = Card('♠', '7')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 0)

    def test_eight_is_0_points(self):
        """8 should be 0 points."""
        card = Card('♥', '8')
        pts = TrickResolver.get_card_points(card, 'HOKUM', '♠')
        self.assertEqual(pts, 0)

    def test_sun_mode_no_trump_bonuses(self):
        """In SUN mode, J and 9 should NOT get trump bonuses."""
        jack = Card('♠', 'J')
        nine = Card('♠', '9')
        pts_j = TrickResolver.get_card_points(jack, 'SUN')
        pts_9 = TrickResolver.get_card_points(nine, 'SUN')
        self.assertEqual(pts_j, 2)  # Normal Jack value
        self.assertEqual(pts_9, 0)  # Normal 9 value

    def test_sun_total_points(self):
        """SUN mode total per suit should be A(11)+10(10)+K(4)+Q(3)+J(2) = 30."""
        suit = '♥'
        total = sum(
            TrickResolver.get_card_points(Card(suit, r), 'SUN')
            for r in ['A', '10', 'K', 'Q', 'J', '9', '8', '7']
        )
        self.assertEqual(total, 30)


class TestGetTrickWinner(unittest.TestCase):
    """Tests for TrickResolver.get_trick_winner."""

    def test_highest_lead_suit_wins_sun(self):
        """In SUN, highest card of lead suit wins."""
        table = [
            {'card': Card('♥', 'K'), 'player_index': 0},
            {'card': Card('♥', 'A'), 'player_index': 1},
            {'card': Card('♥', 'Q'), 'player_index': 2},
            {'card': Card('♥', 'J'), 'player_index': 3},
        ]
        winner = TrickResolver.get_trick_winner(table, 'SUN')
        self.assertEqual(winner, 1)  # Ace wins

    def test_trump_beats_lead_suit(self):
        """In HOKUM, trump card beats higher lead-suit card."""
        table = [
            {'card': Card('♥', 'A'), 'player_index': 0},
            {'card': Card('♠', '7'), 'player_index': 1},  # Trump
            {'card': Card('♥', 'K'), 'player_index': 2},
            {'card': Card('♥', 'Q'), 'player_index': 3},
        ]
        winner = TrickResolver.get_trick_winner(table, 'HOKUM', '♠')
        self.assertEqual(winner, 1)  # Trump 7 beats A♥

    def test_highest_trump_wins(self):
        """When multiple trumps played, highest trump wins."""
        table = [
            {'card': Card('♥', 'A'), 'player_index': 0},
            {'card': Card('♠', '7'), 'player_index': 1},
            {'card': Card('♠', 'J'), 'player_index': 2},  # J is highest in HOKUM
            {'card': Card('♠', '9'), 'player_index': 3},
        ]
        winner = TrickResolver.get_trick_winner(table, 'HOKUM', '♠')
        self.assertEqual(winner, 2)  # J♠ is highest trump

    def test_off_suit_cannot_win_sun(self):
        """In SUN, off-suit cards cannot win."""
        table = [
            {'card': Card('♥', '7'), 'player_index': 0},
            {'card': Card('♠', 'A'), 'player_index': 1},
            {'card': Card('♦', 'A'), 'player_index': 2},
            {'card': Card('♣', 'A'), 'player_index': 3},
        ]
        winner = TrickResolver.get_trick_winner(table, 'SUN')
        self.assertEqual(winner, 0)  # Only ♥ 7 matches lead suit


class TestCanBeatTrump(unittest.TestCase):
    """Tests for TrickResolver.can_beat_trump."""

    def test_higher_trump_can_beat(self):
        """Should return True if hand has a higher trump card."""
        winning_card = Card('♠', '9')
        hand = [Card('♠', 'J'), Card('♥', 'A')]  # J♠ > 9♠
        can_beat, beaters = TrickResolver.can_beat_trump(winning_card, hand, '♠')
        self.assertTrue(can_beat)
        # Check that J♠ is among beaters
        beater_strs = [f"{c.rank}{c.suit}" for c in beaters]
        self.assertIn('J♠', beater_strs)

    def test_lower_trump_cannot_beat(self):
        """Should return False if hand only has lower trumps."""
        winning_card = Card('♠', 'J')  # J is highest
        hand = [Card('♠', '7'), Card('♥', 'A')]
        can_beat, beaters = TrickResolver.can_beat_trump(winning_card, hand, '♠')
        self.assertFalse(can_beat)

    def test_no_trumps_cannot_beat(self):
        """Should return False if hand has no trump cards."""
        winning_card = Card('♠', '7')
        hand = [Card('♥', 'A'), Card('♦', 'K')]
        can_beat, beaters = TrickResolver.can_beat_trump(winning_card, hand, '♠')
        self.assertFalse(can_beat)


if __name__ == '__main__':
    unittest.main()
