import redis
import json
import time
import requests
import uuid

REDIS_URL = "redis://127.0.0.1:6379/0"
API_URL = "http://127.0.0.1:3005/react-py4web/ai_thoughts"

def test_thoughts_flow():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    # 1. Prepare Task
    game_id = f"test_game_{uuid.uuid4().hex[:8]}"
    player_idx = 1
    context_hash = f"hash_{uuid.uuid4().hex[:8]}"
    
    payload = {
        'context_hash': context_hash,
        'timestamp': time.time(),
        'game_id': game_id,
        'player_index': player_idx,
        'game_context': {
            'phase': 'PLAYING',
            'mode': 'SUN',
            'trump': None,
            'hand': ['AS', 'KS', 'QS'],
            'table': [],
            'played_cards': [], # History of played cards
            'score_us': 0,
            'score_them': 0
        }
    }
    
    print(f"[TEST] 1. Pushing task for Game {game_id} Player {player_idx}")
    r.lpush("bot:analyze_queue", json.dumps(payload))
    
    # 2. Wait for Worker (Simulate processing time)
    # NOTE: AI Worker MUST be running for this to work!
    print("[TEST] 2. Waiting for AI Worker...")
    found = False
    for i in range(15):
        time.sleep(1)
        # Check Redis directly
        val = r.get(f"bot:thought:{game_id}:{player_idx}")
        if val:
            print(f"[TEST] Success! Found thought in Redis: {val[:50]}...")
            found = True
            break
        print(f"   ... waiting {i+1}s")
        
    if not found:
        print("[TEST] FAILED: Worker did not save thought to Redis. Is the worker running?")
        return

    # 3. Test API Endpoint
    print(f"[TEST] 3. Testing API Endpoint: {API_URL}/{game_id}")
    try:
        resp = requests.get(f"{API_URL}/{game_id}")
        if resp.status_code == 200:
            data = resp.json()
            thoughts = data.get('thoughts', {})
            if str(player_idx) in thoughts:
                print(f"[TEST] API Success! Retrieved thought: {str(thoughts[str(player_idx)])[:50]}...")
            else:
                print(f"[TEST] API Warning: returned 200 but missing player index. Data: {data}")
        else:
            print(f"[TEST] API Failed: Status {resp.status_code}")
    except Exception as e:
        print(f"[TEST] API Exception: {e}")

if __name__ == "__main__":
    test_thoughts_flow()
