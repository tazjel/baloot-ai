import unittest
from unittest.mock import MagicMock, patch
from ai_worker.professor import Professor
from game_engine.models.card import Card
from game_engine.logic.game import Game

class TestProfessorMechanics(unittest.TestCase):
    def setUp(self):
        self.professor = Professor()
        self.professor.enabled = True
        
        # Mock Game and Player
        self.mock_game = MagicMock(spec=Game)
        self.mock_player = MagicMock()
        self.mock_player.hand = [
            Card('H', 'A'), # Index 0
            Card('H', 'K'), # Index 1
            Card('D', '7')  # Index 2
        ]
        self.mock_game.players = [self.mock_player]
        self.mock_game.get_game_state.return_value = {}

    @patch('ai_worker.professor.BotContext')
    def test_no_blunder_when_optimal(self, MockBotContext):
        """If human plays the best move, no warning."""
        # Mock Context
        MockBotContext.return_value = MagicMock()

        # Mock Analysis: Best move is 0 (Ace)
        analysis_result = {
            'best_move': 0,
            'move_values': {
                0: {'win_rate': 0.8},
                1: {'win_rate': 0.6},
                2: {'win_rate': 0.1}
            }
        }
        self.professor.cognitive.analyze_position = MagicMock(return_value=analysis_result)
        
        # Human plays 0
        result = self.professor.check_move(self.mock_game, 0, 0)
        self.assertIsNone(result)

    @patch('ai_worker.professor.BotContext')
    def test_blunder_detection(self, MockBotContext):
        """If human plays a much worse move, trigger BLUNDER."""
        MockBotContext.return_value = MagicMock()

        # Mock Analysis: Best move is 0 (Ace, 0.8), Human plays 2 (7, 0.1)
        # Diff = 0.7 > 0.25 (Threshold)
        analysis_result = {
            'best_move': 0,
            'move_values': {
                0: {'win_rate': 0.8},
                1: {'win_rate': 0.6},
                2: {'win_rate': 0.1}
            }
        }
        self.professor.cognitive.analyze_position = MagicMock(return_value=analysis_result)
        
        # Human plays 2
        result = self.professor.check_move(self.mock_game, 0, 2)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'BLUNDER')
        self.assertIn("better.", result['reason']) # +70% better

    @patch('ai_worker.professor.BotContext')
    def test_mistake_detection(self, MockBotContext):
        """If human plays a moderately worse move, trigger MISTAKE."""
        MockBotContext.return_value = MagicMock()
        
        # Mock Analysis: Best move is 0 (Ace, 0.8), Human plays 1 (King, 0.6)
        # Diff = 0.2. Thresholds: Blunder=0.25, Mistake=0.15
        # Should be MISTAKE
        analysis_result = {
            'best_move': 0,
            'move_values': {
                0: {'win_rate': 0.8},
                1: {'win_rate': 0.6},
                2: {'win_rate': 0.1}
            }
        }
        self.professor.cognitive.analyze_position = MagicMock(return_value=analysis_result)
        
        # Human plays 1
        result = self.professor.check_move(self.mock_game, 0, 1)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'MISTAKE')

    @patch('ai_worker.professor.BotContext')
    def test_ignore_minor_diff(self, MockBotContext):
        """If human plays a slightly worse move, ignore it."""
        MockBotContext.return_value = MagicMock()

        # Mock Analysis: Best move is 0 (Ace, 0.8), Human plays 1 (King, 0.78)
        # Diff = 0.02.
        analysis_result = {
            'best_move': 0,
            'move_values': {
                0: {'win_rate': 0.8},
                1: {'win_rate': 0.78},
                2: {'win_rate': 0.1}
            }
        }
        self.professor.cognitive.analyze_position = MagicMock(return_value=analysis_result)
        
        # Human plays 1
        result = self.professor.check_move(self.mock_game, 0, 1)
        
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
