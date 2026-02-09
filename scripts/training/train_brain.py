import json
import os
import redis
import hashlib
import time

# Settings
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from server.settings import REDIS_URL
except ImportError:
    print("Warning: Could not import settings. Using default 127.0.0.1")
    REDIS_URL = "redis://127.0.0.1:6379/0"

def train_brain(mistakes_file):
    """
    Reads mistakes JSON and populates Redis with Correct Moves.
    """
    if not os.path.exists(mistakes_file):
        print(f"Error: File {mistakes_file} not found.")
        return

    print(f"Connecting to Redis at {REDIS_URL}...")
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        print(f"Redis Connection Failed: {e}")
        return

    print(f"Loading mistakes from {mistakes_file}...")
    with open(mistakes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = 0
    for match in data:
        analysis = match.get('analysis', {})
        moments = analysis.get('moments', [])
        
        for m in moments:
            correct_move = m.get('correct_move')
            context_hash = m.get('context_hash') # In real flow, we'd need to re-compute this from state
            
            if correct_move and context_hash:
                # Store in Redis
                key = f"brain:correct:{context_hash}"
                value = json.dumps(correct_move)
                
                r.set(key, value)
                print(f"Learned: {key} -> {value}")
                count += 1
            else:
                # If hash missing, we normally re-compute it if state data existed. 
                # For manual test, we skip.
                pass

    print(f"Training Complete. Learned {count} new moves.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="candidates/mistakes_manual.json", help="Path to mistakes JSON")
    args = parser.parse_args()
    
    train_brain(args.file)
