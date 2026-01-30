
import sys
import os
from pathlib import Path
import json

# Add project root
sys.path.append(str(Path(__file__).parent.parent.parent))

from ai_worker.bot_context import BotContext
from game_engine.models.card import Card

def create_mock_state():
    return {
        'players': [
            {'hand': [{'suit': 'H', 'rank': 'A'}, {'suit': 'D', 'rank': '10'}], 'position': 'Bottom', 'team': 'Us'},
            {'hand': [], 'position': 'Right', 'team': 'Them'},
            {'hand': [], 'position': 'Top', 'team': 'Us'}, 
            {'hand': [], 'position': 'Left', 'team': 'Them'}
        ],
        'phase': 'PLAY_PHASE',
        'gameMode': 'SUN',
        'trumpSuit': None,
        'bid': {'type': 'SUN', 'bidder': 'Bottom'},
        'tricks': [
             # One completed trick
             {
                 'cards': [
                     {'suit': 'H', 'rank': '7'}, # Played by Bottom
                     {'suit': 'H', 'rank': '8'}, # Right
                     {'suit': 'H', 'rank': '9'}, # Top
                     {'suit': 'H', 'rank': '10'} # Left
                 ],
                 'winner': 'Left'
             }
        ],
        'tableCards': [
            # Current trick partial
            {'card': {'suit': 'D', 'rank': '7'}, 'playedBy': 'Bottom'}
        ]
    }

def test_mind_integration():
    print("Testing MindReader Integration...")
    
    state = create_mock_state()
    # P0 context
    context = BotContext(state, 0)
    
    try:
        guesses = context.guess_hands()
        if guesses is None:
            print("FAIL: guess_hands() returned None. Is model loaded?")
            return
            
        print("PASS: guess_hands() returned predictions.")
        print(f"Keys: {list(guesses.keys())} (Expected [1, 2, 3])")
        
        # Check specific output
        # Player 1 (Right) predictions
        p1_probs = guesses[1]
        print(f"Player 1 Probabilities Sample: {p1_probs[:5]}")
        
        if len(p1_probs) == 32:
             print("PASS: Valid probability vector size (32).")
        else:
             print(f"FAIL: Invalid vector size {len(p1_probs)}")
             
    except Exception as e:
        print(f"FAIL: Exception raised: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mind_integration()
