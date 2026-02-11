
import unittest
import sys
import os

# Add parent directory to path to import game modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_logic import Game, Card, Player

from server.room_manager import RoomManager
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
        """Test Akka: King is boss after Ace and Ten have been played."""
        p1 = self.game.players[0]
        # Give K, Q Hearts — Ace and 10 are NOT in hand
        p1.hand = [Card('♥', 'K'), Card('♥', 'Q')]
        
        # Ace and 10 of Hearts were played in a previous trick
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
        print(f"Eligible Suits: {eligible_suits}")
        self.assertIn('♥', eligible_suits)
        
    def test_akka_eligibility_king_after_ace_played(self):
        """Test Akka with King after Ace and Ten are gone"""
        p1 = self.game.players[0]
        p1.hand = [Card('♥', 'K'), Card('♥', 'Q')]
        
        # Simulate Ace being played in previous trick
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

    def test_handle_akka_valid(self):
        """Test handle_akka with a valid boss card updates state."""
        p1 = self.game.players[0]
        p1.hand = [Card('♥', 'K'), Card('♦', '7')]
        
        # Ace of Hearts already played
        self.game.round_history.append({
            'cards': [
                {'rank': 'A', 'suit': '♥', 'playedBy': 'Right'},
                {'rank': '10', 'suit': '♥', 'playedBy': 'Top'},
                {'rank': '8', 'suit': '♥', 'playedBy': 'Left'},
                {'rank': '9', 'suit': '♥', 'playedBy': 'Bottom'}
            ],
            'winner': 'Right'
        })
        
        res = self.game.handle_akka(0)
        
        self.assertTrue(res['success'])
        self.assertTrue(self.game.akka_state.active)
        self.assertIn('♥', self.game.akka_state.suits)
        self.assertEqual(self.game.akka_state.claimer, p1.position)

    def test_handle_akka_invalid(self):
        """Test handle_akka when not eligible is rejected."""
        p1 = self.game.players[0]
        # Low cards — no suit qualifies as boss
        p1.hand = [Card('♥', '7'), Card('♥', '8')] 
        
        res = self.game.handle_akka(0)
        
        self.assertFalse(res.get('success'))
        self.assertIn('error', res)
        # Akka state must remain inactive
        self.assertFalse(self.game.akka_state.active)

if __name__ == '__main__':
    unittest.main()

