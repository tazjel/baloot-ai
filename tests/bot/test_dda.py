import unittest
from unittest.mock import MagicMock
from ai_worker.cognitive import CognitiveOptimizer
from ai_worker.bot_context import BotContext

class TestDDA(unittest.TestCase):
    def setUp(self):
        self.optimizer = CognitiveOptimizer(use_inference=False)
        self.ctx = MagicMock(spec=BotContext)
        self.ctx.raw_state = {}

    def test_mercy_rule(self):
        """Test that budget is reduced when winning big"""
        # Us: 100, Them: 20 -> Diff: +80
        self.ctx.raw_state = { 'matchScores': {'us': 100, 'them': 20} }
        
        budget = self.optimizer._calculate_budget(self.ctx)
        self.assertEqual(budget, 500, "Should use Mercy budget (500) when winning by >50")

    def test_panic_rule(self):
        """Test that budget is increased when losing big"""
        # Us: 20, Them: 100 -> Diff: -80
        self.ctx.raw_state = { 'matchScores': {'us': 20, 'them': 100} }
        
        budget = self.optimizer._calculate_budget(self.ctx)
        self.assertEqual(budget, 5000, "Should use Panic budget (5000) when losing by >50")

    def test_neutral_rule(self):
        """Test that base budget is used in close games"""
        # Us: 50, Them: 40 -> Diff: +10
        self.ctx.raw_state = { 'matchScores': {'us': 50, 'them': 40} }
        
        budget = self.optimizer._calculate_budget(self.ctx)
        self.assertEqual(budget, 2000, "Should use Base budget (2000) in close games")

    def test_mcts_respects_limit(self):
        """Test that MCTSSolver stops at max_iterations"""
        from ai_worker.mcts.mcts import MCTSSolver
        from ai_worker.mcts.fast_game import FastGame
        
        solver = MCTSSolver()
        mock_game = MagicMock(spec=FastGame)
        mock_game.get_legal_moves.return_value = [0, 1]
        mock_game.clone.return_value = mock_game
        # Fix: is_terminal must be True so rollout finishes immediately
        mock_game.is_terminal.return_value = True 
        mock_game.scores = {'us': 0, 'them': 0}
        
        # MCTS needs teams/turn to check for adversarial toggle
        mock_game.teams = ['us', 'them', 'us', 'them']
        mock_game.current_turn = 0
        
        # Run with limit 5
        _, details = solver.search_with_details(mock_game, timeout_ms=5000, max_iterations=5)
        
        # Calculate total visits
        total_visits = sum(d['visits'] for d in details.values())
        
        # It might do 1 extra due to expansion or initial node, but it should be close to 5
        # The loop condition is `iterations >= max_iterations`
        # Each loop creates one node.
        # With max_iterations=5, it runs 5 times.
        # Total visits should match.
        
        # Note: visits are incremented during backprop.
        # If we run 5 iterations, we do 5 backprops.
        self.assertLessEqual(total_visits, 6, "Should not significantly exceed max_iterations")
        self.assertGreaterEqual(total_visits, 5, "Should verify at least max_iterations")

if __name__ == '__main__':
    unittest.main()
