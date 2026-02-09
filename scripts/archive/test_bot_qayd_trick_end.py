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

def test_qayd_trick_end():
    print("=== Testing Bot Qayd Trigger (End of Trick/Empty Table) ===")
    
    # 1. Mock Game State where table is EMPTY (resolved)
    # But lastTrick contains the illegal move
    mock_state = {
        'gameId': 'test_qayd_lat_trick',
        'phase': 'PLAYING',
        'gameMode': 'SUN',
        'trumpSuit': 'H',
        'tableCards': [], # EMPTY!
        'lastTrick': {
             'cards': [
                 {'suit': 'D', 'rank': 'J'},
                 {'suit': 'D', 'rank': '9'},
                 {'suit': 'D', 'rank': 'A'},
                 {'suit': 'S', 'rank': '7'} # Illegal move?
             ],
             'metadata': [
                 None,
                 None,
                 None,
                 {'is_illegal': True, 'violation': 'REVOKE'} # The Smoking Gun
             ],
             'winner': 'Right'
        },
        'players': [
            {'position': 'Bottom', 'name': 'Bot', 'hand': [], 'team': 'us'}, # Me
            {'position': 'Right', 'name': 'Opponent', 'hand': [], 'team': 'them'},
            {'position': 'Top', 'name': 'Partner', 'hand': [], 'team': 'us'},
            {'position': 'Left', 'name': 'Opponent', 'hand': [], 'team': 'them'},
        ],
        'qaydState': {'active': False},
        'sawaState': {'active': False}
    }
    
    # 2. Initialize Context & Referee
    ctx = BotContext(mock_state, 0) # Bottom Player
    referee = RefereeObserver()
    
    # 3. Check for Qayd
    print(f"Checking Qayd for player {ctx.position} with EMPTY table but suspicious Last Trick...")
    decision = referee.check_qayd(ctx, mock_state)
    
    if decision and decision['action'] == 'QAYD_TRIGGER':
        print("✅ SUCCESS: Bot triggered Qayd from LAST TRICK history!")
        print(f"   Reasoning: {decision.get('reasoning')}")
        return True
    else:
        print(f"❌ FAILURE: Bot missed the crime in the past trick. Got: {decision}")
        return False

if __name__ == "__main__":
    test_qayd_trick_end()
