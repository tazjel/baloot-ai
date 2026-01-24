
import unittest
from game_logic import Game, GamePhase
from ai_worker.agent import ai_worker.agent
import time
import random

class TestStressGame(unittest.TestCase):
    def setUp(self):
        self.game = Game("stress_test_room")
        # Add 4 players
        self.players = []
        for i in range(4):
            # Pos sequence: Bottom, Right, Top, Left
            # indices: 0, 1, 2, 3
            p = self.game.add_player(f"bot_{i}", f"Bot {i}")
            p.is_bot = True # Mark all as bots
            self.players.append(p)
            
    def test_full_round_simulation(self):
        """Simulate a FULL round with random valid actions"""
        print("\n--- Starting Stress Test Simulation ---")
        
        # Start Game
        self.assertTrue(self.game.start_game())
        
        # Limit loop to prevent infinite hang
        max_steps = 1000
        step = 0
        
        while self.game.phase != GamePhase.FINISHED.value and step < max_steps:
            step += 1
            current_idx = self.game.current_turn
            current_player = self.game.players[current_idx]
            
            # Simple Bot Decision
            decision = bot_agent.get_decision(self.game.get_game_state(), current_idx)
            
            # Execute Action
            if self.game.phase == GamePhase.BIDDING.value:
                action = decision.get('action') or 'PASS'
                suit = decision.get('suit')
                res = self.game.handle_bid(current_idx, action, suit)
                if not res.get('success'):
                     # Fallback to PASS if logic failed
                     self.game.handle_bid(current_idx, 'PASS')
                     
            elif self.game.phase == GamePhase.PLAYING.value:
                card_idx = decision.get('cardIndex')
                if card_idx is None:
                     # Fallback random
                     pass # Should handle invalid via game logic
                
                res = self.game.play_card(current_idx, card_idx)
                if not res.get('success'):
                     print(f"Bot {current_idx} failed to play {card_idx}: {res.get('error')}")
                     # Try finding ANY valid card
                     valid_indices = []
                     for i, c in enumerate(current_player.hand):
                          # Check validity manually? Or just try all
                          valid_indices.append(i)
                     
                     played = False
                     for idx in valid_indices:
                          r = self.game.play_card(current_idx, idx)
                          if r['success']: 
                               played = True
                               break
                     
                     if not played:
                          # This implies Bot has NO valid moves or bug.
                          # Check if hand empty?
                          if not current_player.hand:
                               print("Hand Empty but turn active??")
                          else:
                               self.fail(f"Bot {current_idx} STUCK with hand {current_player.hand}")
            
            # Check if game finished
            if self.game.phase == GamePhase.FINISHED.value:
                 print("\n--- Round Finished Successfully ---")
                 print(f"Scores: Us={self.game.match_scores['us']}, Them={self.game.match_scores['them']}")
                 print(f"Bid: {self.game.bid}")
                 break
                 
        if step >= max_steps:
             self.fail("Game Loop Timeout / Infinite Loop")

if __name__ == '__main__':
    unittest.main()
