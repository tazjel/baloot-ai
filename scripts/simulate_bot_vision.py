
import sys
import os
import logging

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Mock Logger
logging.basicConfig(level=logging.INFO)

from ai_worker.agent import BotAgent
from game_engine.models.card import Card

def test_bot_vision():
    print("=== Testing Bot Vision (Is Illegal Flag Visible?) ===")
    
    # 1. Setup Bot
    agent = BotAgent()
    
    # 2. Construct Game State with Illegal Move
    # P2 played Ace Hearts (Illegal)
    card_illegal = Card('♥', 'A')
    
    game_state = {
        'gameId': 'viz_test',
        'players': [
            {'name': 'Me', 'index': 0, 'team': 'us', 'hand': [{'rank': '7', 'suit': '♠'}]},
            {'name': 'Bot', 'index': 1, 'team': 'them', 'profile': 'Sherlock', 'hand': [{'rank': '9', 'suit': '♣'}]},
            {'name': 'Partner', 'index': 2, 'team': 'us', 'hand': []},
            {'name': 'Right', 'index': 3, 'team': 'them', 'hand': []}
        ],
        'tableCards': [
            {
                'playerId': 'P_RIGHT', 
                'playedBy': 'Right', 
                'card': card_illegal.to_dict(), 
                'metadata': {'is_illegal': True, 'illegal_reason': 'REVOKE'}
            }
        ],
        'fullMatchHistory': [],
        'qaydState': {'active': False}, # Not active yet, we want to TRIGGER it
        'phase': 'PLAYING',
        'currentTurnIndex': 1, # Bot's turn
        'dealer': 0,
        'bid': {'type': 'SUN', 'bidder': 0}
    }
    
    # 3. Ask Bot for Decision
    print("Asking Bot (Index 1) for decision...")
    decision = agent.get_decision(game_state, 1)
    
    print(f"Bot Decision: {decision}")
    
    # 4. Verify
    if decision.get('action') == 'QAYD_ACCUSATION':
        print("✅ SUCCESS: Bot saw the illegal move and accused!")
    elif decision.get('action') == 'QAYD_TRIGGER':
        print("✅ SUCCESS: Bot triggered Qayd!")
    else:
        print("❌ FAILURE: Bot missed it. Action: ", decision.get('action'))

if __name__ == "__main__":
    test_bot_vision()
