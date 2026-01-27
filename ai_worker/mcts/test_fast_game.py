
import unittest
import sys
import os

# Path hack
sys.path.append(os.getcwd())

from game_engine.models.card import Card
from ai_worker.mcts.fast_game import FastGame

class TestFastGame(unittest.TestCase):
    
    def test_sun_logic(self):
        # Setup: Sun Game, 1 Cards each
        hands = [
            [Card('S','A')], # Bottom
            [Card('S','10')], # Right
            [Card('S','K')], # Top
            [Card('S','7')]  # Left
        ]
        
        game = FastGame(hands, trump=None, mode='SUN', current_turn=0, dealer_index=0)
        
        # Bottom Plays A
        moves = game.get_legal_moves()
        self.assertEqual(moves, [0])
        game.apply_move(0)
        
        # Right Plays 10
        game.apply_move(0)
        # Top Plays K
        game.apply_move(0)
        # Left Plays 7
        game.apply_move(0)
        
        # Bottom should win (A > 10 > K > 7)
        # Points: A(11) + 10(10) + K(4) + 7(0) = 25
        # Last Trick Bonus = 10 -> Total 35
        
        self.assertTrue(game.is_terminal())
        self.assertEqual(game.scores['us'], 35)
        self.assertEqual(game.scores['them'], 0)

    def test_hokum_trump_logic(self):
        # Trump is Spades
        hands = [
            [Card('D','A')],  # Bottom (Leads Diamond)
            [Card('D','7')],  # Right (Has D)
            [Card('H','7')],  # Top (Void D, No Trump)
            [Card('S','7')]   # Left (Void D, Has Trump 7)
        ]
        game = FastGame(hands, trump='S', mode='HOKUM', current_turn=0, dealer_index=0)
        
        # Bottom Plays DA
        game.apply_move(0)
        
        # Right follows D7
        game.apply_move(0)
        
        # Top discards H7
        game.apply_move(0)
        
        # Left Trumps with S7
        game.apply_move(0)
        
        # Left should win
        self.assertTrue(game.is_terminal())
        self.assertEqual(game.tricks_collected['them'], 1)
        # Points: A(11) + 10(Last) = 21 (Assuming others are 0)
        self.assertEqual(game.scores['them'], 21)

if __name__ == '__main__':
    unittest.main()
