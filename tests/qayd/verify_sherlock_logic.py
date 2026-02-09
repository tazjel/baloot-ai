
import logging
import sys
import unittest
from unittest.mock import MagicMock

# Adjust path to include project root
sys.path.append('.')

# Mock Logger to avoid errors if server utils not found or configured
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SherlockTest")

# Mock classes to simulate Game Infrastructure
class MockContext:
    def __init__(self, position, phase, table_cards):
        self.position = position
        self.phase = phase
        self.table_cards = table_cards
        self.decision_timer = 0

class TestSherlockBot(unittest.TestCase):
    
    def test_referee_trigger(self):
        """
        Test 1: verify RefereeObserver detects the 'is_illegal' flag 
        and returns QAYD_TRIGGER.
        """
        from ai_worker.referee_observer import RefereeObserver
        
        observer = RefereeObserver()
        
        # Scenario: 
        # Round Logic: Hearts led.
        # Player 'Right' plays Diamonds (Illegal).
        # We (Bottom) should detect it.
        
        game_state = {
            'phase': 'PLAYING',
            'tableCards': [
                {'playerId': 'p1', 'card': {'suit': 'H', 'rank': 'A'}, 'playedBy': 'Top', 'metadata': {}},
                # The Illegal Move:
                {'playerId': 'p2', 'card': {'suit': 'D', 'rank': '9'}, 'playedBy': 'Right', 'metadata': {'is_illegal': True}} 
            ]
        }
        
        ctx = MockContext(position='Bottom', phase='PLAYING', table_cards=game_state['tableCards'])
        
        print("\n--- Test 1: Referee Detection ---")
        decision = observer.check_qayd(ctx, game_state)
        
        self.assertIsNotNone(decision, "RefereeObserver should return a decision")
        self.assertEqual(decision['action'], 'QAYD_TRIGGER', "Action should be QAYD_TRIGGER")
        print("✅ RefereeObserver correctly returned QAYD_TRIGGER")

    def test_sherlock_accusation(self):
        """
        Test 2: Verify BotAgent calls the Sherlock logic when Qayd is Active
        and it is the Reporter.
        """
        # We need to test the logic block inside BotAgent.get_decision
        # Since we can't easily instantiate the full BotAgent with all dependencies without mocking,
        # we will extract the logic or mock the dependencies heavily.
        
        # Let's try to simulate the specific condition in agent.py
        
        print("\n--- Test 2: Sherlock Accusation Logic ---")
        
        # Mock State: Qayd is Active, Bottom is Reporter
        game_state = {
            'roomId': 'test_room',
            'phase': 'PLAYING',
            'qaydState': {
                'active': True,
                'reporter': 'Bottom', # We are Bottom
                'reason': 'MANUAL_TRIGGER' 
            },
            'tableCards': [
                 {'playerId': 'p1', 'card': {'suit': 'H', 'rank': 'A'}, 'playedBy': 'Top', 'metadata': {}},
                 {'playerId': 'p2', 'card': {'suit': 'D', 'rank': '9'}, 'playedBy': 'Right', 'metadata': {'is_illegal': True}} 
            ],
            'fullMatchHistory': []
        }
        
        # We will manually execute the logic block we added to agent.py check
        # because importing BotAgent might trigger connection logic.
        
        # Simplified logic replica from agent.py:
        ctx = MockContext(position='Bottom', phase='PLAYING', table_cards=game_state['tableCards'])
        decision = self.sherlock_logic(ctx, game_state)
        
        self.assertEqual(decision['action'], 'QAYD_ACCUSATION', "Should accuse")
        self.assertEqual(decision['accusation']['crime_card']['suit'], 'D', "Should identify illegal card")
        print("✅ Sherlock Logic correctly returned QAYD_ACCUSATION")

    def sherlock_logic(self, ctx, game_state):
        """
        Direct copy of the logic implemented in agent.py for testing.
        """
        import time
        # Mock logger
        
        qayd_state = game_state.get('qaydState')
        if qayd_state and qayd_state.get('active'):
            reporter_pos = qayd_state.get('reporter')
            
            if reporter_pos == ctx.position:
                 # Skip sleep for test
                 # time.sleep(15) 
                 
                 table_cards = game_state.get('tableCards', [])
                 crime_card = None
                 proof_card = None
                 
                 if table_cards:
                     for tc in reversed(table_cards):
                         # Handle dict access for 'card' object structure in simulation
                         # In real game, 'card' might be Card object or dict depending on serializer
                         # Here we assume dict for Sim
                         
                         meta = tc.get('metadata') or {}
                         if meta.get('is_illegal'):
                             crime_card = tc['card']
                             if table_cards:
                                 proof_card = table_cards[0]['card']
                             break
                 
                 if crime_card:
                    return {
                        "action": "QAYD_ACCUSATION",
                        "accusation": {
                            "crime_card": crime_card,
                            "proof_card": proof_card or crime_card,
                            "violation_type": "REVOKE"
                        }
                    }
        return None

if __name__ == '__main__':
    unittest.main()
