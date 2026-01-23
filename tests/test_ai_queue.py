import sys
import os
import json
import time
import hashlib
import redis

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env.local'))

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

def push_task():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    context = {
        'mode': 'SUN',
        'trump': None,
        'hand': [{'rank': 'A', 'suit': '♠'}, {'rank': '10', 'suit': '♠'}],
        'table': [],
        'position': 'Bottom',
        'phase': 'BIDDING', # Test Bidding
        'currentBid': {'type': 'PASS'},
        'scores': {'us': 0, 'them': 0},
        'dealerIndex': 0,
        'myIndex': 1,
        'round': 1
    }
    
    state_str = json.dumps(context, sort_keys=True)
    context_hash = hashlib.md5(state_str.encode()).hexdigest()
    
    payload = {
        'context_hash': context_hash,
        'timestamp': time.time(),
        'game_context': context
    }
    
    print(f"Pushing task {context_hash} to queue...")
    r.lpush("bot:analyze_queue", json.dumps(payload))
    
    # Poll for result
    print("Waiting for result...")
    for i in range(10):
        res = r.get(f"bot:move:{context_hash}")
        if res:
            print(f"\nSUCCESS! AI Brain Reply: {res}")
            return
        time.sleep(1)
        print(".", end="", flush=True)
        
    print("\nTIMEOUT: No result from worker.")

if __name__ == "__main__":
    push_task()
