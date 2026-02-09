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

def test_qayd_multicard():
    print("=== Testing Bot Qayd Trigger (Buried in Table) ===")
    
    # 1. Mock Game State
    # Scenario: Right played illegal. Top played Legal. Left played Legal.
    # Now it's Bottom's (Bot) turn.
    mock_state = {
        'gameId': 'test_qayd_buried',
        'phase': 'PLAYING',
        'gameMode': 'SUN',
        'trumpSuit': 'H',
        'tableCards': [
            {
                'card': {'suit': 'H', 'rank': 'A'},
                'playedBy': 'Right',
                'metadata': {'is_illegal': True, 'violation': 'REVOKE'} # BURRIED CRIME
            },
            {
                'card': {'suit': 'H', 'rank': '9'},
                'playedBy': 'Top',
                'metadata': {} # Legal
            },
            {
                'card': {'suit': 'H', 'rank': '7'},
                'playedBy': 'Left',
                'metadata': {} # Legal
            }
        ],
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
    print(f"Checking Qayd for player {ctx.position} with Buried Illegal Move at index 0...")
    decision = referee.check_qayd(ctx, mock_state)
    
    if decision and decision['action'] == 'QAYD_TRIGGER':
        print("✅ SUCCESS: Bot triggered Qayd on BURIED card!")
        print(f"   Reasoning: {decision.get('reasoning')}")
        return True
    else:
        print(f"❌ FAILURE: Bot missed the buried crime. Got: {decision}")
        return False

if __name__ == "__main__":
    test_qayd_multicard()
