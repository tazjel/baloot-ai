
import unittest
from game_engine.logic.game import Game
from game_engine.models.player import Player
from game_engine.logic.rules.projects import compare_projects
from game_engine.models.constants import ORDER_PROJECTS

class MockProject:
    def __init__(self, type, rank, score):
        self.type = type
        self.rank = rank
        self.score = score
        
    def __getitem__(self, item):
        return getattr(self, item)

class TestMashaari(unittest.TestCase):
    def setUp(self):
        self.game = Game("test")
        # Setup 4 players
        self.game.add_player("1", "P1") # Index 0 -> Bottom (US)
        self.game.add_player("2", "P2") # Index 1 -> Right (THEM)
        self.game.add_player("3", "P3") # Index 2 -> Top (US)
        self.game.add_player("4", "P4") # Index 3 -> Left (THEM)
        
        self.game.dealer_index = 0 
        
    def test_compare_projects_score(self):
        # 400 vs 100
        p1 = {'type': 'FOUR_HUNDRED', 'rank': 'A', 'score': 40}
        p2 = {'type': 'HUNDRED', 'rank': 'K', 'score': 20}
        
        # P1 better
        self.assertEqual(compare_projects(p1, p2, 'SUN', 0, 1, 2), 1)
        self.assertEqual(compare_projects(p2, p1, 'SUN', 0, 1, 2), -1)

    def test_compare_projects_rank(self):
        # Sira A vs Sira K
        p1 = {'type': 'SIRA', 'rank': 'A', 'score': 4}
        p2 = {'type': 'SIRA', 'rank': 'K', 'score': 4}
        
        self.assertEqual(compare_projects(p1, p2, 'SUN', 0, 1, 2), 1) # A > K
        
    def test_compare_projects_tie_distance(self):
        # Sira A vs Sira A (Different suits)
        p1 = {'type': 'SIRA', 'rank': 'A', 'score': 4}
        p2 = {'type': 'SIRA', 'rank': 'A', 'score': 4}
        
        # P1 is Index 1 (Dist 0). P2 is Index 2 (Dist 1).
        # P1 Should win.
        self.assertEqual(compare_projects(p1, p2, 'SUN', 0, 1, 2), 1)
        
        # Reverse indices. P1 at Index 2, P2 at Index 1.
        # P2 Should win (return -1).
        self.assertEqual(compare_projects(p1, p2, 'SUN', 0, 2, 1), -1)

    def test_end_round_mashaari_us_wins(self):
        """Test round-end scoring with projects. Us wins Kaboot + projects."""
        # Setup: US bidder with SUN mode
        self.game.bid = {'bidder': 'Bottom', 'type': 'SUN', 'doubled': False}
        self.game.game_mode = 'SUN'
        
        # Competing project declarations
        self.game.declarations = {
            'Top': [{'type': 'SIRA', 'rank': 'A', 'score': 4}],    # P3 (Us)
            'Right': [{'type': 'SIRA', 'rank': 'K', 'score': 4}]   # P2 (Them)
        }
        
        # Us wins ALL 8 tricks -> KABOOT (44 points in SUN)
        self.game.round_history = []
        for _ in range(8):
            self.game.round_history.append({
                'winner': 'Bottom', 'points': 100, 'cards': [], 'playedBy': []
            })
        self.game.match_scores = {'us': 0, 'them': 0}
        
        self.game.end_round(skip_scoring=False)
        
        # Us: 44 (Kaboot) + project GP. 
        # Us wins SIRA A vs SIRA K -> Us gets 4 abnat project.
        # SUN project GP: (4 * 2) // 10 = 0 (rounded down).
        # Total Us = 44 + 0 = 44. No Khasara (Us > Them).
        self.assertEqual(self.game.match_scores['us'], 44)
        self.assertEqual(self.game.match_scores['them'], 0)

    def test_end_round_mashaari_tie_breaker(self):
        """Tied Projects: Sira A vs Sira A. Closer player wins."""
        # Bidder Them, SUN mode.
        self.game.bid = {'bidder': 'Right', 'type': 'SUN', 'doubled': False}
        self.game.game_mode = 'SUN'

        self.game.declarations = {
            'Top': [{'type': 'SIRA', 'rank': 'A', 'score': 4}],    # Us (Idx 2)
            'Right': [{'type': 'SIRA', 'rank': 'A', 'score': 4}]   # Them (Idx 1) -> Closer, wins
        }
        
        # Them gets ALL tricks -> KABOOT (44) for Them
        self.game.round_history = []
        for _ in range(8):
            self.game.round_history.append({
                'winner': 'Right', 'points': 100, 'cards': [], 'playedBy': []
            })
        self.game.match_scores = {'us': 0, 'them': 0}
        
        self.game.end_round(skip_scoring=False)
        
        # Them: 44 (Kaboot). No Khasara (They are bidder and won).
        self.assertEqual(self.game.match_scores['us'], 0) 
        self.assertEqual(self.game.match_scores['them'], 44)

if __name__ == '__main__':
    unittest.main()
