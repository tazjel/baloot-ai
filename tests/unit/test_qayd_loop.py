import unittest
from unittest.mock import MagicMock, patch
import sys

# Adjust path
sys.path.append('.')

# Mock BotContext to avoid complex dependencies
class MockContext:
    def __init__(self, game_state, player_index, personality=None):
        self.phase = game_state.get('phase')
        self.position = 'Bottom'
        self.player_index = player_index
        self.team = 'us'
        self.players_team_map = {'Bottom': 'us', 'Right': 'them'}
        self.hand = []
        self.table_cards = game_state.get('tableCards', [])
        self.memory = MagicMock()
        self.memory.check_contradiction.return_value = "Contradiction Found"

class TestQaydLoop(unittest.TestCase):
    def setUp(self):
        # Reset BotAgent singleton state
        from ai_worker.agent import bot_agent
        bot_agent.reported_crimes = set()
        self.agent = bot_agent

    def test_live_detection_loop(self):
        """
        Verify that the Bot enters a loop if 'Live Detection' (Section A)
        does not check reported_crimes.
        """
        print("\n--- Test: Live Detection Loop Risk ---")

        # Scenario: Illegal card on table
        game_state = {
            'phase': 'PLAYING',
            'players': [{'name': 'Bot', 'team': 'us'}],
            'tableCards': [
                {'card': {'suit': 'H', 'rank': 'A'}, 'playedBy': 'Right', 'metadata': {}}
            ],
            'currentRoundTricks': [],
            'roundHistory': [], # round_num = 0
            'qaydState': {'active': False}
        }

        # Patch BotContext to return our mock
        with patch('ai_worker.agent.BotContext', side_effect=MockContext) as mock_ctx_cls:

            # 1. First Call -> Should Trigger
            decision1 = self.agent.get_decision(game_state, 0)
            print(f"Call 1 Decision: {decision1}")

            self.assertEqual(decision1.get('action'), 'QAYD_TRIGGER', "First call should trigger Qayd")

            # 2. Simulate TrickManager rejecting it (so game state doesn't change)
            # Bot is called again.

            # IF BUG EXISTS: It will trigger again (Loop)
            # IF FIXED: It should not trigger (return PASS or something else) because it remembers the crime.

            decision2 = self.agent.get_decision(game_state, 0)
            print(f"Call 2 Decision: {decision2}")

            # We EXPECT this to FAIL if the bug is present (it triggers again).
            # The test confirms the existence of the bug if decision2 is QAYD_TRIGGER.

            if decision2.get('action') == 'QAYD_TRIGGER':
                 print("!!! BUG REPRODUCED: Bot triggered Qayd again on same state !!!")
                 self.fail("Infinite Loop Detected: Bot keeps triggering Qayd on same state.")
            else:
                 print("No Loop: Bot respected anti-spam.")

if __name__ == '__main__':
    unittest.main()
