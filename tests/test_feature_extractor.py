
import unittest
from unittest.mock import MagicMock
from ai_worker.learning.feature_extractor import FeatureExtractor
from ai_worker.bot_context import BotContext
from game_engine.models.card import Card
from ai_worker.memory import CardMemory

class TestFeatureExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = FeatureExtractor()
        self.ctx = MagicMock(spec=BotContext)
        self.ctx.hand = []
        self.ctx.memory = MagicMock(spec=CardMemory)
        self.ctx.memory.played_cards = set()
        self.ctx.raw_state = {}
        self.ctx.trump = 'S'
        self.ctx.mode = 'SUN'

    def test_hand_encoding(self):
        """Test that hand cards are encoded correctly"""
        # Spades 7 (First card in standard ordering S, H, D, C | 7..A)
        # S7 should be index 0
        c = Card('S', '7')
        self.ctx.hand = [c]
        
        vec = self.extractor.encode(self.ctx)
        
        self.assertEqual(vec[0], 1.0, "Spades 7 should be index 0")
        self.assertEqual(sum(vec[:32]), 1.0, "Only 1 card in hand")

    def test_dimensions(self):
        """Test vector size is exactly 138"""
        vec = self.extractor.encode(self.ctx)
        self.assertEqual(len(vec), 138)

if __name__ == '__main__':
    unittest.main()
