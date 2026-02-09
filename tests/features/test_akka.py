
import unittest
import sys
import os

# Add parent directory to path to import game modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_logic import Game, Card, Player

from room_manager import RoomManager
from game_logic import ORDER_HOKUM, ORDER_SUN

class TestAkkaLogic(unittest.TestCase):
    def setUp(self):
        self.game = Game("test_room")
        # Debug: Check play_card signature
        import inspect
        print(f"DEBUG: play_card args: {inspect.getfullargspec(Game.play_card)}")
        
        self.game.add_player("p1", "Player 1")
        self.game.add_player("p2", "Player 2")
        self.game.add_player("p3", "Player 3")
        self.game.add_player("p4", "Player 4")
        
        # Manually set up game state for testing to avoid randomness
        self.game.players[0].hand = [] # Clear hands
        
        # Start game (generates deck)
        self.game.start_game()
        
        # Force HOKUM mode
        # By bypassing handle_bid which is complex, we just set state
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        self.game.phase = 'PLAYING'
        self.game.current_turn = 0
        self.game.table_cards = []
        self.game.round_history = []
        
    def test_akka_eligibility_simple(self):
        """Test simplest Akka scenario: Leading with Ace of non-trump"""
        p1 = self.game.players[0]
        # Give him A, K Hearts
        p1.hand = [Card('♥', 'A'), Card('♥', 'K')]
        
        # Check eligibility
        eligible_suits = self.game.check_akka_eligibility(0)
        print(f"Eligible Suits: {eligible_suits}")
        self.assertIn('♥', eligible_suits)
        
    def test_akka_eligibility_king_after_ace_played(self):
        """Test Akka with King after Ace is gone"""
        p1 = self.game.players[0]
        p1.hand = [Card('♥', 'K'), Card('♥', 'Q')]
        
        # Simulate Ace being played in previous trick
        # round_history structure: [{'cards': [{'rank': 'A', 'suit': '♥', ...}, ...], 'winner': ...}]
        self.game.round_history.append({
            'cards': [
                {'rank': 'A', 'suit': '♥', 'playedBy': 'Right'},
                {'rank': '10', 'suit': '♥', 'playedBy': 'Top'},
                {'rank': '8', 'suit': '♥', 'playedBy': 'Left'},
                {'rank': '9', 'suit': '♥', 'playedBy': 'Bottom'}
            ],
            'winner': 'Right'
        })
        
        eligible_suits = self.game.check_akka_eligibility(0)
        print(f"Eligible Suits (King): {eligible_suits}")
        self.assertIn('♥', eligible_suits)

    def test_play_card_with_akka(self):
        """Test playing a card with Akka metadata updates state"""
        p1 = self.game.players[0]
        p1.hand = [Card('♥', 'A'), Card('♦', '7')]
        
        # Play Ace with Akka
        # We need to make sure it is valid move
        # Table empty, leading Ace. Valid.
        
        res = self.game.play_card(0, 0, metadata={'akka': True})
        
        if not res.get('success'):
             print(f"Play Card Failed: {res}")
             
        self.assertTrue(res['success'])
        self.assertIsNotNone(self.game.akka_state)
        self.assertEqual(self.game.akka_state['suit'], '♥')
        self.assertEqual(self.game.akka_state['claimer'], p1.position)

    def test_play_card_invalid_akka(self):
        """Test playing Akka when not eligible"""
        p1 = self.game.players[0]
        p1.hand = [Card('♥', '7'), Card('♥', '8')] 
        # Ace is NOT played. 7 is low.
        
        # Try to play 7 with Akka
        res = self.game.play_card(0, 0, metadata={'akka': True})
        
        self.assertFalse(res.get('success'))
        self.assertIn('error', res)
        # Ensure akka_state is NOT set
        self.assertIsNone(self.game.akka_state)

if __name__ == '__main__':
    unittest.main()
