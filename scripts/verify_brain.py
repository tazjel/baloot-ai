import sys
import os
import json
import logging

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set Offline Mode to prevent Real Redis connection attempt
# os.environ["OFFLINE_MODE"] = "true" # Commented out for Production Mode check


from bot_agent import bot_agent
from game_engine.models.card import Card
from ai_worker.mock_redis import MockRedis

from settings import OFFLINE_MODE

def verify_brain():
    
    if OFFLINE_MODE:
        print("Verifying Brain Override (OFFLINE MOCK MODE)...")
        # Inject Mock
        mock_redis = MockRedis()
        bot_agent.redis_client = mock_redis
        
        # Set the test Key
        test_key = "brain:move:FORCE_OVERRIDE_TEST"
        test_val = json.dumps({"action": "PLAY", "suit": "♠", "rank": "A", "reason": "Test Override"})
        mock_redis.set(test_key, test_val)
        
        val = bot_agent.redis_client.get(test_key)
        print(f"Mock Redis Check for '{test_key}': {val}")
        
    else:
        print("Verifying Brain Override (LIVE REDIS MODE)...")
        if not bot_agent.redis_client:
             print("ERROR: BotAgent failed to connect to Redis.")
             return

        # Prepare Real Redis with Test Key
        test_key = "brain:move:FORCE_OVERRIDE_TEST"
        test_val = json.dumps({"action": "PLAY", "suit": "♠", "rank": "A", "reason": "Test Override"})
        bot_agent.redis_client.set(test_key, test_val)
        print(f"Seeded Redis Key: {test_key}")

    
    # Mock Game State
    # We need a state that triggers PLAYING phase
    mock_state = {
        "roomId": "test_room",
        "phase": "PLAYING",
        "gameMode": "SUN",
        "trumpSuit": None,
        "players": [
            {"id": "p0", "name": "Bot", "hand": [], "captured": []},
            {"id": "p1", "name": "R", "hand": [], "captured": []},
            {"id": "p2", "name": "T", "hand": [], "captured": []},
            {"id": "p3", "name": "L", "hand": [], "captured": []}
        ],
        "tableCards": [],
        "currentTurnIndex": 0,
        "dealerIndex": 0,
        "matchScores": {"us": 0, "them": 0},
        "bid": {"type": "SUN", "suit": None}
    }
    
    # We need to ensure the bot has the card we want it to play (Ace of Spades)
    # And maybe a 7-S to check if it would normally play that?
    # Actually, the Brain logic maps Brain Move (Rank/Suit) to an index in hand.
    # So we MUST have the Ace of Spades in hand.
    
    # Let's give it [7-S, A-S]
    # Index 0: 7-S
    # Index 1: A-S
    
    # If Heuristic (Random/Weak) plays 7-S (Index 0).
    # If Brain plays A-S (Index 1).
    
    # Note: bot_agent.py re-constructs BotContext from state.
    # We need to ensure BotContext parses this correctly.
    # BotContext uses `state['players'][idx]['hand']`.
    
    hand = [
        {"rank": "7", "suit": "♠"},
        {"rank": "A", "suit": "♠"}
    ]
    mock_state['players'][0]['hand'] = hand
    
    print(f"Test Hand: {hand}")
    
    # Call Decision
    decision = bot_agent.get_decision(mock_state, 0)
    
    print(f"Decision: {decision}")
    
    if decision.get('cardIndex') == 1:
        print("SUCCESS! Bot chose Index 1 (Ace of Spades) - The Brain Works.")
        if "Brain Override" in decision.get('reasoning', ''):
             print(f"Reasoning confirmed: {decision.get('reasoning')}")
    else:
        print(f"FAILURE. Bot chose Index {decision.get('cardIndex')}. Brain ignored.")

if __name__ == "__main__":
    verify_brain()
