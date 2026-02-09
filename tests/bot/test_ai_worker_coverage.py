import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock Redis (still needed for BrainClient import inside agent)
mock_redis_module = MagicMock()
class MockPubSubWorkerThread: pass
mock_redis_module.client.PubSubWorkerThread = MockPubSubWorkerThread
sys.modules['redis'] = mock_redis_module

from ai_worker.agent import BotAgent, bot_agent
from ai_worker.personality import BALANCED

class TestAIWorkerCoverage:
    
    @pytest.fixture
    def mock_game_state(self):
        return {
            'phase': 'BIDDING',
            'players': [
                {'index': 0, 'name': 'Bot1', 'hand': [{'rank': 'A', 'suit': 'S', 'id': 'AS'}], 'is_bot': True},
                {'index': 1, 'name': 'Player2', 'hand': [], 'is_bot': False},
                {'index': 2, 'name': 'Player3', 'hand': [], 'is_bot': False},
                {'index': 3, 'name': 'Dealer', 'hand': [], 'is_bot': False}
            ],
            'currentTurnIndex': 0,
            'dealerIndex': 3,
            'floorCard': {'rank': '7', 'suit': 'H', 'id': '7H'},
            'scores': {'us': 0, 'them': 0},
            'matchScores': {'us': 0, 'them': 0},
            'bid': None,
            'sawaState': {'active': False},
            'gameId': 'mock_game_1'
        }

    def test_get_decision_bidding_pass(self, mock_game_state):
        """Verify bot passes with weak hand (Brain returns None)"""
        # Mock BrainClient on the instance
        with patch.object(bot_agent.brain, 'lookup_move', return_value=None):
             # Mock Strategy to return PASS (via integration or just ensure logic falls through)
             # BiddingStrategy defaults are verified elsewhere, here we test the flow
             
             decision = bot_agent.get_decision(mock_game_state, 0)
             
             # Fallback logic should reach strategy or default
             # Given weak hand, strategy likely outputs PASS
             assert decision['action'] == 'PASS'


    def test_brain_override(self, mock_game_state):
        """Verify bot uses brain move if found by BrainClient"""
        mock_brain_move = {"action": "PLAY", "rank": "A", "suit": "S", "reason": "Strategic Win"}
        
        mock_game_state['phase'] = 'PLAYING'
        mock_game_state['bid'] = {'type': 'HOKUM', 'bidder': 1}
        
        with patch.object(bot_agent.brain, 'lookup_move', return_value=mock_brain_move):
            
            decision = bot_agent.get_decision(mock_game_state, 0)
            
            assert decision['action'] == 'PLAY'
            assert decision['cardIndex'] == 0
            assert "Brain Override" in decision['reasoning']

    def test_referee_qayd(self, mock_game_state):
        """Verify referee intercepts illegal move with Qayd claim"""
        mock_game_state['phase'] = 'PLAYING'
        mock_game_state['tableCards'] = [
             {'card': {'rank': 'K', 'suit': 'D'}, 'playedBy': 1, 'metadata': {'is_illegal': True}}
        ]
        
        # Test direct referee check via Agent
        # Note: BotAgent calls self.referee.check_qayd
        
        decision = bot_agent.get_decision(mock_game_state, 0)
        
        assert decision['action'] == 'QAYD_CLAIM'

    def test_referee_sawa(self, mock_game_state):
        """Verify referee responds to Sawa claim"""
        # Setup Sawa State: Player 1 (Opponent) claims Sawa
        mock_game_state['sawaState'] = {
            'active': True,
            'status': 'PENDING',
            'claimer': 'Right', # Assuming Player 1 is Right relative to Bot (0)
            'responses': {}
        }
        # Bot needs context to know positions, mock it via ctx or raw state
        # BotContext derives position from player data.
        mock_game_state['players'][0]['position'] = 'Bottom'
        mock_game_state['players'][1]['position'] = 'Right'
        
        # Test: Bot should respond (ACCEPT by default if no masters)
        decision = bot_agent.get_decision(mock_game_state, 0)
        
        assert decision['action'] == 'SAWA_RESPONSE'
        assert decision['response'] in ['ACCEPT', 'REFUSE']
