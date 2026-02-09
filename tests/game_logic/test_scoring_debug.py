import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from game_logic import Game, Player

class TestScoringDebug(unittest.TestCase):
    def setUp(self):
        self.game = Game("debug_room")
        self.game.add_player("p1", "Player 1") # Bottom (US)
        self.game.add_player("p2", "Player 2") # Right (THEM)
        self.game.add_player("p3", "Player 3") # Top (US)
        self.game.add_player("p4", "Player 4") # Left (THEM)
        
        self.game.game_mode = 'HOKUM'
        self.game.bid = {"type": "HOKUM", "bidder": "Bottom", "doubled": False} # US Bidder

    def test_hokum_split_scoring(self):
        """
        Simulate a game where US (Bidder) gets 122 points and THEM gets 40 points.
        Expected: US gets 12, THEM gets 4. (Total 16).
        Bug Risk: If system thinks THEM bid, it sees 40 < 81, so THEM Khasara -> US 16, THEM 0.
        """
        
        # Simulate tricks summing to 122 and 40
        # Total 162.
        
        self.game.round_history = []
        
        # US (Bottom) takes big tricks. Total 112 + 10 (Last) = 122.
        # THEM (Right) takes small tricks. Total 40.
        
        # Trick 1: THEM. Points 40.
        self.game.round_history.append({'winner': 'Right', 'points': 40, 'cards': [], 'playedBy': []})
        # Trick 2: US. Points 50.
        self.game.round_history.append({'winner': 'Bottom', 'points': 50, 'cards': [], 'playedBy': []})
        # Trick 3: US. Points 62. (Last Trick -> Bonus to US)
        self.game.round_history.append({'winner': 'Bottom', 'points': 62, 'cards': [], 'playedBy': []})
        
        # US needs last trick for +10 bonus to reach 122 from 112?
        # Trick 2 was last? No need many tricks.
        # Just ensure last item in list is winner Bottom.
        
        self.game.end_round()
        
        print(f"Match Scores: {self.game.match_scores}")
        print(f"Past Round Results: {self.game.past_round_results[-1]}")
        
        # Check raw points
        raw_us = self.game.past_round_results[-1]['us']['abnat']
        raw_them = self.game.past_round_results[-1]['them']['abnat']
        
        print(f"Raw US: {raw_us} (Expected 122)")
        print(f"Raw THEM: {raw_them} (Expected 40)")
        
        
        # Check game points
        score_us = self.game.past_round_results[-1]['us']['result']
        score_them = self.game.past_round_results[-1]['them']['result']
        
        print(f"DEBUG RESULTS: US={score_us} THEM={score_them}")
        print(f"Raw US: {raw_us} Raw THEM: {raw_them}")
        print(f"Bid: {self.game.bid}")
        
        self.assertEqual(score_us, 12, f"US should have 12 points. Got {score_us}")
        self.assertEqual(score_them, 4, f"THEM should have 4 points. Got {score_them}")

if __name__ == '__main__':
    unittest.main()
