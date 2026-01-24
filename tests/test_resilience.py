
from game_logic import Game
import unittest
import logging

# Mute logging for test
logging.basicConfig(level=logging.CRITICAL)

class TestGameResilience(unittest.TestCase):
    def setUp(self):
        self.game = Game("test_room")
        self.p0 = self.game.add_player("p0", "Player 0")
        self.p1 = self.game.add_player("p1", "Player 1")
        self.p2 = self.game.add_player("p2", "Player 2")
        self.p3 = self.game.add_player("p3", "Player 3")
        self.game.start_game()

    def test_invalid_bid_action(self):
        """Test sending garbage action to handle_bid"""
        res = self.game.handle_bid(self.game.current_turn, "GARBAGE_ACTION")
        # Should return error, NOT crash
        self.assertIn('error', res)
        print(f"Invalid Bid Result: {res}")

    def test_bid_out_of_turn(self):
        """Test bidding when not turn"""
        wrong_player = (self.game.current_turn + 1) % 4
        res = self.game.handle_bid(wrong_player, "PASS")
        self.assertIn('error', res)
        print(f"Out of Turn Bid Result: {res}")

    def test_play_card_invalid_index(self):
        """Test playing card with index out of bounds"""
        # Fast forward to playing phase
        # Everyone pass -> Round 2 -> Everyone Pass -> Redeal (Reset)
        # Force phase
        self.game.phase = "PLAYING"
        self.game.current_turn = 0
        self.game.players[0].hand = [1, 2, 3] # Mock hand
        
        # Try index 100
        res = self.game.play_card(0, 100)
        self.assertIn('error', res)
        print(f"Invalid Card Index Result: {res}")

    def test_play_card_wrong_phase(self):
        self.game.phase = "BIDDING"
        res = self.game.play_card(0, 0)
        self.assertIn('error', res)

    def test_declare_project_invalid(self):
        res = self.game.handle_declare_project(0, "SUPER_SECRET_PROJECT")
        self.assertIn('error', res)
        print(f"Invalid Project Result: {res}")

if __name__ == '__main__':
    unittest.main()
