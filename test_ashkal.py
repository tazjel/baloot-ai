
import unittest
from game_logic import Game, Player, GamePhase

class TestAshkal(unittest.TestCase):
    def setUp(self):
        self.game = Game("test")
        # Add 4 players
        # Index assignments:
        # P1 -> Index 0 (Dealer) - Position Bottom?
        # Game add_player logic: first added is first in list.
        # Dealer Index default is 0.
        
        self.game.add_player("1", "Dealer") # Idx 0
        self.game.add_player("2", "Right")  # Idx 1
        self.game.add_player("3", "Partner")# Idx 2
        self.game.add_player("4", "Left")   # Idx 3
        
        self.game.dealer_index = 0
        self.game.phase = GamePhase.BIDDING.value
        self.game.bidding_round = 1
        
        # Mock deal
        # Note: sort_hand expects Unicode Suit symbols ♠, ♥, ♣, ♦
        self.game.floor_card = type('Card', (object,), {'suit': '♠', 'rank': 'A', 'to_dict': lambda: {}})()
        for p in self.game.players:
             p.hand = [] # Empty hand mock

    def test_ashkal_valid_dealer(self):
        # Dealer is Index 0.
        # It must be Dealer's turn to bid? 
        # Ashkal button only appears when it's your turn.
        self.game.current_turn = 0 
        
        res = self.game.handle_bid(0, "ASHKAL")
        self.assertTrue(res.get("success"), f"Dealer should be allowed to Ashkal. Error: {res.get('error')}")
        self.assertEqual(self.game.game_mode, "SUN")
        # Player 0 is Bottom usually in standard deal
        self.assertEqual(self.game.bid['bidder'], "Bottom")

    def test_ashkal_valid_left_opponent(self):
        # Left of Dealer (0) is Index 3. 
        self.game.current_turn = 3
        
        res = self.game.handle_bid(3, "ASHKAL")
        self.assertTrue(res.get("success"), f"Left Opponent should be allowed to Ashkal. Error: {res.get('error')}")
        self.assertEqual(self.game.game_mode, "SUN")
        self.assertEqual(self.game.bid['bidder'], "Left")
        
    def test_ashkal_invalid_right_opponent(self):
        # Right of Dealer (0) is Index 1.
        self.game.current_turn = 1
        
        res = self.game.handle_bid(1, "ASHKAL")
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("error"), "Only Dealer or Left Opponent can call Ashkal")

    def test_ashkal_invalid_partner(self):
        # Partner of Dealer (0) is Index 2.
        self.game.current_turn = 2
        
        res = self.game.handle_bid(2, "ASHKAL")
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("error"), "Only Dealer or Left Opponent can call Ashkal")

    def test_ashkal_valid_round_2(self):
        self.game.bidding_round = 2
        self.game.current_turn = 0 # Dealer
        
        res = self.game.handle_bid(0, "ASHKAL")
        self.assertTrue(res.get("success"), "Ashkal should be allowed in Round 2")
        self.assertEqual(self.game.game_mode, "SUN")

if __name__ == '__main__':
    unittest.main()
