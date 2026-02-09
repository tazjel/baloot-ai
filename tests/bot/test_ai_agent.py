import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Ensure we can import from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_worker.agent import BotAgent
from ai_worker.bot_context import BotContext

class TestBotAgent(unittest.TestCase):
    def setUp(self):
        # Patch Redis to avoid connection attempts
        self.redis_patcher = patch('ai_worker.agent.redis')
        self.mock_redis_module = self.redis_patcher.start()
        
        # Instantiate fresh agent
        self.agent = BotAgent()
        
        # Mock Strategies
        self.agent.bidding_strategy = MagicMock()
        self.agent.playing_strategy = MagicMock()
        
        # Mock Redis Client
        self.mock_redis_client = MagicMock()
        self.agent.redis_client = self.mock_redis_client

    def tearDown(self):
        self.redis_patcher.stop()

    def get_mock_game_state(self, phase="BIDDING"):
        return {
            'phase': phase,
            'players': [
                {'name': 'Me', 'hand': [], 'position': 'Bottom'},
                {'name': 'Right', 'hand': [], 'position': 'Right'},
                {'name': 'Top', 'hand': [], 'position': 'Top'},
                {'name': 'Left', 'hand': [], 'position': 'Left'}
            ],
            'currentTurnIndex': 0,
            'dealerIndex': 3,
            'bid': {},
            'tableCards': [],
            'matchScores': {'us': 0, 'them': 0},
            'sawaState': {'active': False},
            'biddingRound': 1,
            'floorCard': {'suit': 'S', 'rank': 'A'}
        }

    def test_bidding_delegation(self):
        state = self.get_mock_game_state("BIDDING")
        self.agent.bidding_strategy.get_decision.return_value = {"action": "PASS"}
        
        # Make redis return None (no brain override)
        self.mock_redis_client.get.return_value = None

        decision = self.agent.get_decision(state, 0)
        
        self.agent.bidding_strategy.get_decision.assert_called()
        self.assertEqual(decision['action'], "PASS")

    def test_playing_delegation(self):
        state = self.get_mock_game_state("PLAYING")
        self.agent.playing_strategy.get_decision.return_value = {"action": "PLAY", "cardIndex": 0}
        
        self.mock_redis_client.get.return_value = None

        decision = self.agent.get_decision(state, 0)
        
        self.agent.playing_strategy.get_decision.assert_called()
        self.assertEqual(decision['action'], "PLAY")

    def test_brain_override_playing(self):
        state = self.get_mock_game_state("PLAYING")
        # Player has Ace of Spades
        state['players'][0]['hand'] = [{'suit': 'S', 'rank': 'A', 'value': 4}] # Simplified Card
        
        # Brain says play Ace of Spades
        brain_move = {"rank": "A", "suit": "S", "reason": "Win Trick"}
        self.mock_redis_client.get.return_value = json.dumps(brain_move)
        
        decision = self.agent.get_decision(state, 0)
        
        # We expect cardIndex 0 because that matches A-S
        self.assertEqual(decision['action'], "PLAY")
        self.assertEqual(decision['cardIndex'], 0)
        self.assertIn("Brain Override", decision.get('reasoning', ''))

    def test_sawa_refusal(self):
        # Setup Sawa Scenario
        state = self.get_mock_game_state("PLAYING")
        state['sawaState'] = {
            'active': True,
            'status': 'PENDING',
            'claimer': 'Right', # Enemy
            'responses': {}
        }
        
        # Give Master Card (Ace of Spades in SUN mode)
        # Note: We need a valid context to check master card.
        # BotAgent uses BotContext internally. 
        # But we need mock hand to contain a master card.
        # Assuming Ace is master.
        state['players'][0]['hand'] = [{'suit': 'S', 'rank': 'A', 'value': 4}]
        state['bid'] = {'type': 'SUN'} # SUN Mode
        
        decision = self.agent.get_decision(state, 0)
        
        self.assertEqual(decision['action'], "SAWA_RESPONSE")
        self.assertEqual(decision['response'], "REFUSE")

if __name__ == '__main__':
    unittest.main()
