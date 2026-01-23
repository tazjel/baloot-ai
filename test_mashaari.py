
import unittest
from game_logic import Game, Player, compare_projects, ORDER_PROJECTS

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
        self.game.add_player("1", "P1") # Dealer + 1 (Right) -> Index 0
        self.game.add_player("2", "P2") # Dealer + 2 (Top) -> Index 1
        self.game.add_player("3", "P3") # Dealer + 3 (Left) -> Index 2
        self.game.add_player("4", "P4") # Dealer (Bottom) -> Index 3 ?? 
        
        # Dealer Index logic in Game:
        # self.dealer_index = 0 initially.
        # current_turn = (dealer + 1) % 4 => 1.
        # Play Order: 1, 2, 3, 0.
        # Distance from Dealer (0):
        # P1 (Idx 1): (1 - 1) % 4 = 0 (Closest)
        # P2 (Idx 2): (2 - 1) % 4 = 1
        # P3 (Idx 3): (3 - 1) % 4 = 2
        # P4 (Idx 0): (0 - 1) % 4 = 3 (Furthest)
        
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
        # Sira A vs Sira A (Different suits, usually impossible for Sequence? 
        # Actually possible: P1 has hearts A-K-Q, P2 has spades A-K-Q.
        
        p1 = {'type': 'SIRA', 'rank': 'A', 'score': 4}
        p2 = {'type': 'SIRA', 'rank': 'A', 'score': 4}
        
        # P1 is Index 1 (Dist 0). P2 is Index 2 (Dist 1).
        # P1 Should win.
        self.assertEqual(compare_projects(p1, p2, 'SUN', 0, 1, 2), 1)
        
        # Reverse indices. P1 at Index 2, P2 at Index 1.
        # P2 Should win (return -1).
        self.assertEqual(compare_projects(p1, p2, 'SUN', 0, 2, 1), -1)

    def test_end_round_mashaari_us_wins(self):
        # Setup: Us (P1, P3) vs Them (P2, P4).
        
        # Avoid Khasara: Make Us the Bidder and give score > 13.
        self.game.bid = {'bidder': 'Bottom', 'type': 'SUN', 'doubled': False} # Bidder Us
        self.game.game_mode = 'SUN'
        
        # declarations
        self.game.declarations = {
            'Top': [{'type': 'SIRA', 'rank': 'A', 'score': 4}], # P3 (Us)
            'Right': [{'type': 'SIRA', 'rank': 'K', 'score': 4}] # P2 (Them)
        }
        
        # Give Us enough points (e.g. 100 raw -> 20 game points)
        self.game.round_history = [{'winner': 'Bottom', 'points': 100, 'cards': []}]
        self.game.match_scores = {'us': 0, 'them': 0}
        
        self.game.end_round(skip_scoring=False)
        
        # Us Points: 
        # Cards: 100 raw + 10 last trick = 110. /10 * 2 = 22.
        # Projects: 4 (Us wins Sira A vs K).
        # Total Us = 26.
        # Them = 0.
        
        # Khasara check: Bidder (Us) has 26 > 13. No Khasara.
        
        self.assertEqual(self.game.match_scores['us'], 26)
        self.assertEqual(self.game.match_scores['them'], 0)

    def test_end_round_mashaari_tie_breaker(self):
        # Tied Projects: Sira A vs Sira A.
        # Them (Right, P2) is Closer. Them wins project.
        
        # Avoid Khasara: Bidder Them. Give points.
        self.game.bid = {'bidder': 'Right', 'type': 'SUN', 'doubled': False} # Bidder Them
        self.game.game_mode = 'SUN'

        self.game.declarations = {
            'Top': [{'type': 'SIRA', 'rank': 'A', 'score': 4}], # Us (Idx 2)
            'Right': [{'type': 'SIRA', 'rank': 'A', 'score': 4}] # Them (Idx 1) -> Winner
        }
        
        # Them gets card points
        self.game.round_history = [{'winner': 'Right', 'points': 100, 'cards': []}]
        self.game.match_scores = {'us': 0, 'them': 0}
        
        self.game.end_round(skip_scoring=False)
        
        # Them:
        # Cards: 110 -> 22.
        # Projects: 4.
        # Total: 26.
        # Us: 0.
        
        self.assertEqual(self.game.match_scores['us'], 0) 
        self.assertEqual(self.game.match_scores['them'], 26)

if __name__ == '__main__':
    unittest.main()
