import sys
import os
import logging

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from ai_worker.bot_context import BotContext
from ai_worker.referee_observer import RefereeObserver

# Setup Logger
logging.basicConfig(level=logging.INFO)

def test_qayd_trigger():
    print("=== Testing Bot Qayd Trigger ===")
    
    # 1. Mock Game State with Illegal Move
    mock_state = {
        'gameId': 'test_qayd_1',
        'phase': 'PLAYING',
        'gameMode': 'SUN',
        'trumpSuit': 'H',
        'tableCards': [
            {
                'card': {'suit': 'H', 'rank': 'A'},
                'playedBy': 'Right',
                'metadata': {'is_illegal': True, 'violation': 'REVOKE'}
            }
        ],
        'players': [
            {'position': 'Bottom', 'name': 'Bot', 'hand': [], 'team': 'us'}, # Me
            {'position': 'Right', 'name': 'Opponent', 'hand': [], 'team': 'them'},
            {'position': 'Top', 'name': 'Partner', 'hand': [], 'team': 'us'},
            {'position': 'Left', 'name': 'Opponent', 'hand': [], 'team': 'them'},
        ],
        'qaydState': {'active': False}, # Not yet active
        'sawaState': {'active': False}
    }
    
    # 2. Initialize Context & Referee
    ctx = BotContext(mock_state, 0) # Bottom Player
    referee = RefereeObserver()
    
    # 3. Check for Qayd
    print(f"Checking Qayd for player {ctx.position}...")
    decision = referee.check_qayd(ctx, mock_state)
    
    if decision and decision['action'] == 'QAYD_TRIGGER':
        print("✅ SUCCESS: Bot triggered Qayd correctly!")
        print(f"   Reasoning: {decision.get('reasoning')}")
        return True
    else:
        print(f"❌ FAILURE: Bot did NOT trigger Qayd. Got: {decision}")
        return False

if __name__ == "__main__":
    test_qayd_trigger()
