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
        # Instantiate fresh agent
        self.agent = BotAgent()
        
        # Mock Strategies
        self.agent.bidding_strategy = MagicMock()
        self.agent.playing_strategy = MagicMock()
        
        # Mock BrainClient to avoid Redis connection
        self.agent.brain = MagicMock()
        self.agent.brain.lookup_move.return_value = None

    def get_mock_game_state(self, phase="BIDDING"):
        return {
            'phase': phase,
            'players': [
                {'name': 'Me', 'hand': [], 'position': 'Bottom', 'index': 0, 'team': 'us'},
                {'name': 'Right', 'hand': [], 'position': 'Right', 'index': 1, 'team': 'them'},
                {'name': 'Top', 'hand': [], 'position': 'Top', 'index': 2, 'team': 'us'},
                {'name': 'Left', 'hand': [], 'position': 'Left', 'index': 3, 'team': 'them'}
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

        decision = self.agent.get_decision(state, 0)
        
        self.agent.bidding_strategy.get_decision.assert_called()
        self.assertEqual(decision['action'], "PASS")

    def test_playing_delegation(self):
        state = self.get_mock_game_state("PLAYING")
        self.agent.playing_strategy.get_decision.return_value = {"action": "PLAY", "cardIndex": 0}

        decision = self.agent.get_decision(state, 0)
        
        self.agent.playing_strategy.get_decision.assert_called()
        self.assertEqual(decision['action'], "PLAY")

    def test_brain_override_playing(self):
        state = self.get_mock_game_state("PLAYING")
        # Player has Ace of Spades
        state['players'][0]['hand'] = [{'suit': 'S', 'rank': 'A', 'value': 4}]
        
        # Brain says play Ace of Spades
        brain_move = {"rank": "A", "suit": "S", "reason": "Win Trick"}
        self.agent.brain.lookup_move.return_value = brain_move
        
        decision = self.agent.get_decision(state, 0)
        
        # We expect cardIndex 0 because that matches A-S
        self.assertEqual(decision['action'], "PLAY")
        self.assertEqual(decision['cardIndex'], 0)
        self.assertIn("Brain Override", decision.get('reasoning', ''))



if __name__ == '__main__':
    unittest.main()

