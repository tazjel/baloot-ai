import unittest
from ai_worker.mcts.mcts import MCTSSolver
from ai_worker.mcts.fast_game import FastGame
from game_engine.models.card import Card

class TestMCTSSolver(unittest.TestCase):
    def test_search_with_details(self):
        # Setup a simple endgame state
        # Bot has Ace Hearts. Opponent has King Hearts.
        # Bot leads.
        
        # Hands: 4 players.
        # P0 (Bot): [Ah]
        # P1: [Kh]
        # P2: [2h]
        # P3: [3h]
        
        # Hands: 4 players.
        # P0 (Bot): [Ah]
        # P1: [Kh]
        # P2: [2h]
        # P3: [3h]
        
        hands = [
            [Card('H', 'A')],
            [Card('H', 'K')],
            [Card('H', '7')],
            [Card('H', '8')]
        ]
        
        game = FastGame(
            players_hands=hands,
            trump='H',
            mode='HOKUM',
            current_turn=0,
            dealer_index=0,
            table_cards=[]
        )
        
        solver = MCTSSolver()
        
        # Run search
        best_move, details = solver.search_with_details(game, timeout_ms=500)
        
        # Check output structure
        self.assertIsInstance(best_move, int)
        self.assertIsInstance(details, dict)
        
        print(f"Best Move: {best_move}")
        print(f"Details: {details}")
        
        # We expect detailed stats for the only move (0)
        self.assertTrue(0 in details)
        stats = details[0]
        self.assertIn('visits', stats)
        self.assertIn('wins', stats)
        self.assertIn('win_rate', stats)
        
        # Since Bot has Ace and it's Hokum/Trump Hearts, Bot should win.
        # P0 plays A. P1 plays K. P2 plays 7. P3 plays 8.
        # P0 wins.
        # Win rate should be 1.0 (or close to 1.0 depending on reward normalization).
        # We calculate reward as 0.5 + score_diff/100.
        # Score diff will be positive (Ace=11 + K=4 + ...).
        
        # We expect win_rate > 0.5
        self.assertGreater(stats['win_rate'], 0.5)

if __name__ == '__main__':
    unittest.main()
