import sys
import os
import json
import logging
import time

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_worker.agent import ai_worker.agent
from dotenv import load_dotenv

# Load env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env.local'))

def test_flywheel():
    print("Testing Data Flywheel...")
    
    if not bot_agent.redis_client:
        print("SKIPPING: No Redis Connection.")
        return

    # Mock Round Snapshot
    snapshot = {
        'roundNumber': 1,
        'winner': 'us',
        'scores': {'us': 26, 'them': 0},
        'timestamp': time.time()
    }
    
    print("Capturing Data...")
    bot_agent.capture_round_data(snapshot)
    
    # Verify Stream
    print("Reading Stream 'analytics:hand_finished'...")
    # Read last entry
    entries = bot_agent.redis_client.xread({'analytics:hand_finished': '0-0'}, count=1)
    
    if entries:
        stream_key, messages = entries[0]
        msg_id, data = messages[0]
        print(f"\nSUCCESS: Found entry in stream!")
        print(f"ID: {msg_id}")
        print(f"Data: {data['data'][:50]}...")
    else:
        print("\nFAILURE: Stream is empty.")

if __name__ == "__main__":
    test_flywheel()
