
import sys
import os
import logging
import unittest
from unittest.mock import MagicMock

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_worker.agent import bot_agent

class TestSherlockTrigger(unittest.TestCase):
    def test_sherlock_triggers_on_illegal_move(self):
        # 1. Mock Game State
        game_state = {
            'gameId': 'test_sherlock',
            'phase': 'PLAYING',
            'tableCards': [
                 # Normal Card
                 {'card': {'suit': 'H', 'rank': '7'}, 'playedBy': 'Top', 'metadata': {}},
                 # Illegal Card!
                 {'card': {'suit': 'D', 'rank': 'K'}, 'playedBy': 'Right', 'metadata': {'is_illegal': True}}
            ],
            'players': [
                {'name': 'Me', 'index': 0, 'hand': []},
                {'name': 'Right', 'index': 1, 'hand': []},
                {'name': 'Partner', 'index': 2, 'hand': []},
                {'name': 'Left', 'index': 3, 'hand': []},
            ],
            'qaydState': {'active': False}
        }
        
        # 2. Call Agent
        decision = bot_agent.get_decision(game_state, 0)
        
        # 3. Verify
        print(f"Decision: {decision}")
        self.assertEqual(decision.get('action'), 'QAYD_TRIGGER')
        
    def test_sherlock_ignores_legal_moves(self):
        # 1. Mock Game State (Clean)
        game_state = {
            'gameId': 'test_item',
            'phase': 'PLAYING',
            'tableCards': [
                 {'card': {'suit': 'H', 'rank': '7'}, 'playedBy': 'Top', 'metadata': {}}
            ],
            'players': [{'name': 'Me', 'index': 0, 'hand': []}],
            'qaydState': {'active': False}
        }
        
        # 2. Call Agent
        decision = bot_agent.get_decision(game_state, 0)
        
        # 3. Verify (Should be just a move or pass, NOT QAYD_TRIGGER)
        print(f"Decision: {decision}")
        self.assertNotEqual(decision.get('action'), 'QAYD_TRIGGER')

    def test_sherlock_triggers_on_last_trick_illegal(self):
        # 1. Mock Game State (Table Empty, Last Trick has Illegal Move)
        game_state = {
            'gameId': 'test_sherlock_last_trick',
            'phase': 'PLAYING',
            'tableCards': [], # Empty!
            'lastTrick': {
                'metadata': [
                    {},
                    {},
                    {},
                    {'is_illegal': True} # The 4th card was BAD
                ]
            },
            'players': [
                {'name': 'Me', 'index': 0, 'hand': []},
                {'name': 'Right', 'index': 1, 'hand': []},
                {'name': 'Partner', 'index': 2, 'hand': []},
                {'name': 'Left', 'index': 3, 'hand': []},
            ],
            'qaydState': {'active': False}
        }
        
        # 2. Call Agent
        decision = bot_agent.get_decision(game_state, 0)
        
        # 3. Verify
        print(f"Decision (Last Trick): {decision}")
        self.assertEqual(decision.get('action'), 'QAYD_TRIGGER')

if __name__ == "__main__":
    unittest.main()
