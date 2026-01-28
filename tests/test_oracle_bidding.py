
import unittest
from unittest.mock import MagicMock
from ai_worker.strategies.oracle_bidding import OracleBiddingStrategy
from ai_worker.bot_context import BotContext
from game_engine.models.card import Card
from ai_worker.memory import CardMemory
from game_engine.models.constants import BiddingPhase

class TestOracleBidding(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleBiddingStrategy()
        
        # Setup specific strong hand
        self.hand = [
            Card('♥', 'A'), Card('♥', '10'), Card('♥', 'K'), Card('♥', 'Q'), 
            Card('♠', 'A'), Card('♠', '10'), Card('♦', 'A'), Card('♣', 'A')
        ]
        
        self.ctx = MagicMock(spec=BotContext)
        self.ctx.hand = self.hand
        self.ctx.memory = CardMemory()
        self.ctx.raw_state = {
            'dealerIndex': 0,
            'currentRoundTricks': [],
            'tableCards': []
        }
        
    def test_strong_hand_valuation(self):
        """Oracle should give high value to a hand with 4 Aces"""
        summary = self.oracle.evaluate_hand(self.ctx)
        
        print("\nOracle Summary:", summary)
        
        print("\nOracle Summary:", summary)
        
        # New API returns 'details' dict
        sun_details = summary['details'].get('SUN', {})
        sun_ev = sun_details.get('ev', 0)
        
        # With 4 Aces + Strong Hearts, we should win almost all tricks.
        # Max score is 152.
        # We should get at least 100.
        
        self.assertGreater(sun_ev, 50, "Strong hand should have high EV")
        self.assertEqual(summary['best_bid'], 'SUN', "Should recommend SUN for 4 Aces")
        
if __name__ == '__main__':
    unittest.main()
