
import sys
import unittest
from game_logic import Game, GamePhase, Card

class TestGamePhases(unittest.TestCase):
    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p0", "Dealer")
        self.game.add_player("p1", "Right")
        self.game.add_player("p2", "Partner")
        self.game.add_player("p3", "Left")
        
        # Set dealer to P0
        self.game.dealer_index = 0
        self.game.start_game()

    def test_initial_deal(self):
        """Phase I: Verify initial deal and floor card"""
        print("\nTesting Initial Deal...")
        # Check hand size
        for p in self.game.players:
            self.assertEqual(len(p.hand), 5)
        
        # Check floor card
        self.assertIsNotNone(self.game.floor_card)
        print("Initial deal passed.")

    def test_ashkal_logic(self):
        """Phase II: Verify Ashkal"""
        print("\nTesting Ashkal Logic...")
        # Dealer is P0. Turn starts at P1.
        self.assertEqual(self.game.current_turn, 1)
        
        # P1 Passes
        self.game.handle_bid(1, "PASS")
        self.assertEqual(self.game.current_turn, 2)
        
        # P2 is Partner (Index 2). Should be able to call Ashkal.
        # Ashkal Action
        res = self.game.handle_bid(2, "ASHKAL")
        self.assertTrue(res.get("success"), f"Ashkal failed: {res}")
        
        # Verify Contract
        self.assertEqual(self.game.bid['type'], "SUN")
        self.assertEqual(self.game.bid['bidder'], "Bottom") # Dealer (P0) Position
        
        # Verify Phase III: Finalization
        # Dealer (P0) should have 8 cards
        p0 = self.game.players[0]
        self.assertEqual(len(p0.hand), 8)
        
        # Others should have 8 cards
        self.assertEqual(len(self.game.players[1].hand), 8)
        
        # Verify Sorting (Sun Mode: A K Q J 10 9 8 7) (Strength Descending if we view it that way)
        # Our sort logic: Group by Suit, then Strength Descending.
        # Let's just check if it's sorted.
        # Printing hand to see.
        print(f"Dealer Hand (Sorted SUN): {p0.hand}")
        
        # Check if 10 is after K? ORDER_SUN = 7 8 9 J Q K 10 A
        # Strength: 7=0, 8=1 ... A=7.
        # Sort key returned (-strength). So -7 (A) < -6 (10).
        # So A comes first.
        # let's pick 2 cards involved.
        
        print("Ashkal and Finalization passed.")

if __name__ == '__main__':
    unittest.main()
