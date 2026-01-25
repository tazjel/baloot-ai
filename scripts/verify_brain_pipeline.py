
import json
import os
import sys
import hashlib
import time

# Ensure we can import from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from ai_worker.agent not bot_agent root if it was moved, 
# but bot_agent.py is in ai_worker based on previous `view_file`.
# Wait, `bot_agent.py` was viewed in `ai_worker/agent.py` but the file listing showed `agent.py`.
# Let's check where `bot_agent` instance is defined. `ai_worker/agent.py` defines class `BotAgent` and instance `bot_agent`.

from ai_worker.agent import bot_agent
from ai_worker.bot_context import BotContext
# from scripts.train_brain import train_brain # We'll call it via subprocess or import if modular
import redis

# Settings
MISTAKES_FILE = "candidates/mistakes_temp.json"
REDIS_URL = "redis://127.0.0.1:6379/0"

def verify_pipeline():
    print("🧠 Verifying The Brain Pipeline...")
    
    # 1. Setup Redis
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        print("✅ Connected to Real Redis")
    except Exception as e:
        print(f"⚠️  Redis Connection Failed: {e}")
        print("⚠️  Switching to MockRedis for Logic Verification...")
        from ai_worker.mock_redis import MockRedis
        r = MockRedis()
        
        # Monkey patch redis for train_brain import if needed, 
        # but train_brain imports `redis`. We might need to inject it.
        # Actually easier: we can't easily patch `train_brain.py`'s internal redis import without sys.modules hack.
        # Let's verify the *Key Generation Logic* and *Bot Retrieval* mainly.
        # For `train_brain`, we might need to modify it to accept a client or Mock it.
        
        # Inject MockRedis into sys.modules to trick train_brain
        import types
        mock_redis_module = types.ModuleType("redis")
        mock_redis_module.from_url = lambda url, **kwargs: r
        sys.modules["redis"] = mock_redis_module
        
        print("✅ MockRedis Injected for verification")

    # 2. Construct a Fake "Match Moment"
    # Scenario: Bot holds [Ace Spades, 7 Spades]. 
    # Valid Play: Ace Spades (Index 1).
    # Bad Play: 7 Spades (Index 0).
    
    hand = [{"rank": "7", "suit": "S"}, {"rank": "A", "suit": "S"}]
    table = []
    
    # Calculate Hash manually to match bot_agent logic
    state_for_hash = {
        'hand': ["7S", "AS"],
        'table': [],
        'phase': "PLAYING",
        'bid': {"type": "SUN", "suit": None},
        'dealer': 0
    }
    state_str = json.dumps(state_for_hash, sort_keys=True)
    context_hash = hashlib.md5(state_str.encode()).hexdigest()
    
    print(f"🔹 Generated Hash: {context_hash}")
    
    # 3. Create Training Data
    training_data = [
        {
            "match_id": "test_match",
            "analysis": {
                "moments": [
                    {
                        "context_hash": context_hash,
                        "correct_move": {"action": "PLAY", "suit": "S", "rank": "A", "reason": "Pipeline Verification"},
                        "bad_move": {"action": "PLAY", "suit": "S", "rank": "7"}
                    }
                ]
            }
        }
    ]
    
    os.makedirs("candidates", exist_ok=True)
    with open(MISTAKES_FILE, 'w') as f:
        json.dump(training_data, f)
        
    print(f"🔹 Created {MISTAKES_FILE}")
    
    # 4. Run Training (Import dynamically to ensure we use the fixed version)
    from scripts.train_brain import train_brain
    print("🔹 Running Training...")
    train_brain(MISTAKES_FILE)
    
    # 5. Verify Redis Key
    key = f"brain:correct:{context_hash}"
    val = r.get(key)
    if not val:
        print(f"❌ Training Failed. Redis key {key} not found.")
        return
    print(f"✅ Redis Key Found: {val}")
    
    # 6. Verify Bot Override
    print("🔹 Verifying Bot Agent Override...")
    
    # Mock Game State for BotAgent
    # Must match the hash components exactly!
    # Card string conversion in bot_agent uses str(Card) -> "RankSuit" (e.g. "AS")
    # We need to ensure the Input to bot_agent results in the same hash.
    
    mock_state = {
        "roomId": "test_room",
        "phase": "PLAYING",
        "gameMode": "SUN",
        "trumpSuit": None,
        "players": [
            {"id": "p0", "name": "Bot", "hand": hand, "captured": []},
            {"id": "p1", "name": "R", "hand": [], "captured": []},
            {"id": "p2", "name": "T", "hand": [], "captured": []},
            {"id": "p3", "name": "L", "hand": [], "captured": []}
        ],
        "tableCards": [], # Empty list of dicts normally
        "currentTurnIndex": 0,
        "dealerIndex": 0,
        "matchScores": {"us": 0, "them": 0},
        "bid": {"type": "SUN", "suit": None}
    }
    
    # Instantiate Bot (connects to Redis)
    bot_agent.redis_client = r 
    
    # Force decision
    # We expect decision to be Index 1 (Ace) because of the learned move "Rank A, Suit S"
    
    decision = bot_agent.get_decision(mock_state, 0)
    print(f"🔹 Bot Decision: {decision}")
    
    if decision.get('action') == 'PLAY' and "Brain" in decision.get('reasoning', ''):
        target_card_idx = decision.get('cardIndex')
        # We know Ace is at index 1
        if target_card_idx == 1:
             print("✅ VERIFICATION PASSED! Bot used the learned move.")
        else:
             print(f"❌ Implementation Error: Bot claimed Brain usage but picked index {target_card_idx} (Expected 1)")
    else:
        print("❌ Verification Failed. Bot did not use Brain override.")

if __name__ == "__main__":
    verify_pipeline()
