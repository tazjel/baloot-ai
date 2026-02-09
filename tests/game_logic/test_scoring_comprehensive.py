import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from game_engine.logic.game import Game

class TestScoringComprehensive(unittest.TestCase):
    def setUp(self):
        self.game = Game("comp_test_room")
        self.game.add_player("p1", "Player 1") # Bottom (US) - Dealer 0
        self.game.add_player("p2", "Player 2") # Right (THEM)
        self.game.add_player("p3", "Player 3") # Top (US)
        self.game.add_player("p4", "Player 4") # Left (THEM)

    def test_sun_project_scoring(self):
        """Test SUN Game with 400 Project for US"""
        self.game.game_mode = 'SUN'
        self.game.bid = {"type": "SUN", "bidder": "Bottom", "doubled": False} # US Bidder

        # Mock Declarations using Dict (not objects, for simplicity in test setup if possible, or simple dicts as game.py handles dicts)
        # Note: game.py expects list of dicts: {'type': '400', 'rank': 'A', 'suit': 'H', 'priority': 1, 'score': 400}
        self.game.declarations = {
            'Bottom': [{'type': '400', 'rank': 'A', 'suit': 'H', 'priority': 1, 'score': 400}],
            'Right': [], 'Top': [], 'Left': []
        }

        # Mock Tricks: Split points evenly 65 - 65 + 10 Last -> 75, 65? 
        # Total Card Points in SUN: 130 + 10 (Last) = 140?? No, standard counting.
        # Let's say US gets 100 raw points, THEM gets 30.
        
        self.game.round_history = [
            {'winner': 'Right', 'points': 30, 'cards': [], 'playedBy': []}, # THEM gets some points
            {'winner': 'Bottom', 'points': 100, 'cards': [], 'playedBy': []}  # US Last trick
        ]
        # Last trick bonus logic needs round_history[-1]
        
        # end_round calculates card abnat. 
        # Raw: US=100 (+10 Last) = 110. THEM=0.
        # US Project: 400.
        # SUN: Project 400 -> 80 pts. Card 110 -> 22 pts. Total 102.
        
        self.game.end_round()
        
        res_us = self.game.past_round_results[-1]['us']
        
        # Expected:
        # Aklat (Pure Card): 100
        # Ardh (Last Trick): 10
        # ProjectPoints: 400
        # Result (Game Points): 
        #   Card: 110 * 2 / 10 = 22.
        #   Project: 400 * 2 / 10 = 80.
        #   Total: 102.
        
        self.assertEqual(res_us['projectPoints'], 400)
        self.assertEqual(res_us['result'], 102)

    def test_kaboot_with_projects(self):
        """Test Kaboot (All Tricks) in HOKUM with Projects"""
        self.game.game_mode = 'HOKUM'
        self.game.bid = {"type": "HOKUM", "bidder": "Bottom"} # US

        # US wins ALL tricks
        self.game.round_history = [
             {'winner': 'Bottom', 'points': 152, 'cards': [], 'playedBy': []}
        ] # Just one entry enough to trigger logic if other team has 0 count

        # US has 100 project
        self.game.declarations = {
            'Top': [{'type': '100', 'rank': 'A', 'suit': 'S', 'priority': 1, 'score': 100}],
             'Bottom': [], 'Right': [], 'Left': []
        }
        
        self.game.end_round()
        
        res_us = self.game.past_round_results[-1]['us']
        res_them = self.game.past_round_results[-1]['them']

        # HOKUM KABOOT = 25 Points.
        # Project 100 in HOKUM = 100 / 10 = 10 Points.
        # Total US = 35.
        # THEM = 0.
        
        self.assertTrue(res_us['isKaboot'])
        self.assertEqual(res_us['result'], 35, f"Expected 35 (25 Kaboot + 10 Proj), got {res_us['result']}")
        self.assertEqual(res_them['result'], 0)

    def test_khasara_scenario(self):
        """Test Khasara: Bidder fails to score > half"""
        self.game.game_mode = 'HOKUM'
        self.game.bid = {"type": "HOKUM", "bidder": "Bottom"} # US Bid

        # US gets 40, THEM gets 122.
        self.game.round_history = [
             {'winner': 'Right', 'points': 112, 'cards': [], 'playedBy': []}, # THEM
             {'winner': 'Bottom', 'points': 40, 'cards': [], 'playedBy': []}, # US
             {'winner': 'Right', 'points': 0, 'cards': [], 'playedBy': []}  # THEM Last trick -> +10
        ]
        
        self.game.end_round()
        
        res_us = self.game.past_round_results[-1]['us']
        res_them = self.game.past_round_results[-1]['them']
        
        # Raw US: 40 -> 4 pts.
        # Raw THEM: 112 + 10 = 122 -> 12 pts.
        # Total 16.
        # Bidder (US) needs > 8. Has 4. -> Khasara.
        # Result: US=0, THEM=16.
        
        self.assertEqual(res_us['result'], 0)
        self.assertEqual(res_them['result'], 16)
        
    def test_doubling_sun(self):
        """Test Doubling (x2) in SUN"""
        self.game.game_mode = 'SUN'
        self.game.bid = {"type": "SUN", "bidder": "Right"} # THEM Bid
        self.game.doubling_level = 2 # Doubled
        
        # Split scores evenly
        self.game.round_history = [
            {'winner': 'Bottom', 'points': 55, 'cards': [], 'playedBy': []}, # US
            {'winner': 'Right', 'points': 65, 'cards': [], 'playedBy': []},  # THEM (+10 Last = 75)
        ]
        # Raw US: 55 -> 11 pts.
        # Raw THEM: 65 + 10 = 75 -> 15 pts.
        # Total 26.
        
        # Doubled:
        # US: 11 * 2 = 22.
        # THEM: 15 * 2 = 30.
        
        self.game.end_round()
        
        res_us = self.game.past_round_results[-1]['us']
        res_them = self.game.past_round_results[-1]['them']
        
        self.assertEqual(res_us['result'], 22)
        self.assertEqual(res_them['result'], 30)


if __name__ == '__main__':
    unittest.main()
