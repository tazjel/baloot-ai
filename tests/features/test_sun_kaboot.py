import unittest
from game_engine.logic.game import Game
from game_engine.models.player import Player
from game_engine.models.card import Card

class TestSunKaboot(unittest.TestCase):
    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p1", "Player 1") # Bottom (US) - Index 0
        self.game.add_player("p2", "Player 2") # Right (THEM) - Index 1
        self.game.add_player("p3", "Player 3") # Top (US) - Index 2
        self.game.add_player("p4", "Player 4") # Left (THEM) - Index 3
        
        self.game.game_mode = 'SUN'
        self.game.bid = {"type": "SUN", "bidder": "Bottom", "doubled": False} # US Bidder

    def test_sun_kaboot_us_wins(self):
        """Test that if US team takes ALL tricks in SUN, they get 44 points."""
        self.game.round_history = []
        
        # 8 Tricks all won by Bottom (US)
        for _ in range(8):
            self.game.round_history.append({
                'winner': 'Bottom',
                'points': 15,
                'cards': [],
                'playedBy': []
            })
            
        self.game.end_round()
        
        print(f"Match Scores: {self.game.match_scores}")
        self.assertEqual(self.game.match_scores['us'], 44, "US Team should have 44 points for Sun Kaboot")
        self.assertEqual(self.game.match_scores['them'], 0, "THEM Team should have 0 points")

    def test_sun_kaboot_them_wins(self):
        """Test that if THEM team takes ALL tricks in SUN, they get 44 points."""
        self.game.round_history = []
        for _ in range(8):
            self.game.round_history.append({
                'winner': 'Right',
                'points': 10,
                'cards': [],
                'playedBy': []
            })
            
        self.game.end_round()
        
        print(f"Match Scores: {self.game.match_scores}")
        self.assertEqual(self.game.match_scores['them'], 44, "THEM Team should have 44 points for Sun Kaboot")
        self.assertEqual(self.game.match_scores['us'], 0, "US Team should have 0 points")

    def test_sun_kaboot_with_projects(self):
        """Test Sun Kaboot + Projects."""
        # US Wins Kaboot (44) + Has a HUNDRED project (100 abnat)
        
        # Mock a project for Bottom (100 abnat for a HUNDRED project)
        self.game.declarations = {
            'Bottom': [{'valid': True, 'score': 100, 'type': 'HUNDRED', 'rank': 'A', 'suit': 'S'}]
        }
        
        self.game.round_history = []
        for _ in range(8):
            self.game.round_history.append({
                'winner': 'Bottom',
                'points': 10,
                'cards': [],
                'playedBy': []
            })
            
        self.game.end_round()
        
        # Kaboot = 44 GP.
        # HUNDRED project: 100 abnat. In SUN: (100 * 2) // 10 = 20 GP.
        # Total: 44 + 20 = 64.
        expected_score = 44 + 20
        print(f"Match Scores with Project: {self.game.match_scores}")
        self.assertEqual(self.game.match_scores['us'], expected_score, f"US Team should have {expected_score} (44 + 20)")

if __name__ == '__main__':
    unittest.main()
