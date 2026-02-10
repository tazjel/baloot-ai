
import unittest
from game_engine.models.card import Card
from game_engine.logic.rules.sawa import check_sawa_eligibility

class TestSawaLogic(unittest.TestCase):
    """
    Test the server-validated Sawa (Grand Slam) eligibility logic.
    
    The old ACCEPT/REFUSE model (where bots evaluated opponent claims) 
    has been removed. Sawa is now server-validated: the engine checks if 
    the declaring player holds the top remaining cards in every suit.
    """

    def test_sawa_eligible_master_sun(self):
        """In SUN, holding the highest remaining cards = eligible."""
        hand = [Card('♥', 'A'), Card('♦', 'A')]
        played = set()  # Nothing played yet, A is highest in SUN
        
        result = check_sawa_eligibility(hand, played, trump_suit=None, game_mode='SUN', phase='PLAYING')
        self.assertTrue(result)

    def test_sawa_not_eligible_weak_hand(self):
        """In SUN, holding 7 and 8 with higher cards still alive = NOT eligible."""
        hand = [Card('♥', '7'), Card('♦', '8')]
        played = set()  # A, 10, K, Q, J, 9 of each suit still alive
        
        result = check_sawa_eligibility(hand, played, trump_suit=None, game_mode='SUN', phase='PLAYING')
        self.assertFalse(result)

    def test_sawa_eligible_after_cards_played(self):
        """If all higher cards are burned, lower cards become masters."""
        hand = [Card('♥', '9')]
        # All cards above 9 in hearts are burned
        played = {'A♥', '10♥', 'K♥', 'Q♥', 'J♥'}
        
        result = check_sawa_eligibility(hand, played, trump_suit=None, game_mode='SUN', phase='PLAYING')
        self.assertTrue(result)

    def test_sawa_not_eligible_gap_in_sequence(self):
        """If there's a gap (missing card held by opponent), NOT eligible."""
        hand = [Card('♥', 'A'), Card('♥', 'Q')]  # Missing 10 and K
        played = set()  # 10 and K are alive, held by opponents
        
        result = check_sawa_eligibility(hand, played, trump_suit=None, game_mode='SUN', phase='PLAYING')
        self.assertFalse(result)

    def test_sawa_eligible_hokum_trump_master(self):
        """In HOKUM, Jack of trump is highest. Holding J+9 of trump = eligible."""
        hand = [Card('♠', 'J'), Card('♠', '9')]
        played = set()  # J is highest trump, 9 is second
        
        result = check_sawa_eligibility(hand, played, trump_suit='♠', game_mode='HOKUM', phase='PLAYING')
        self.assertTrue(result)

    def test_sawa_empty_hand(self):
        """Empty hand should NOT be eligible."""
        result = check_sawa_eligibility([], set(), trump_suit=None, game_mode='SUN', phase='PLAYING')
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
