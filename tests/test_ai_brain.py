import sys
import os
import json
import logging

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_worker.llm_client import GeminiClient
from dotenv import load_dotenv

# Load env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env.local'))

# Configure Logging
logging.basicConfig(level=logging.INFO)

def test_bidding_brain():
    print("Testing Bidding Brain...")
    client = GeminiClient()
    
    if not client.api_key:
        print("SKIPPING: No API Key found.")
        return

    # Mock Bidding Context
    context = {
        'floorCard': {'suit': '♠', 'rank': 'A'},
        'currentBid': None,
        'hand': [
            {'suit': '♠', 'rank': 'K'},
            {'suit': '♠', 'rank': 'Q'},
            {'suit': '♠', 'rank': 'J'},
            {'suit': '♥', 'rank': '7'},
            {'suit': '♦', 'rank': '8'}
        ],
        'scores': {'us': 0, 'them': 0},
        'dealerIndex': 0,
        'myIndex': 0,
        'round': 1
    }
    
    print("Sending Request to Gemini...")
    result = client.analyze_bid(context)
    
    print("\n--- AI Response ---")
    print(json.dumps(result, indent=2))
    
    if result and 'action' in result:
        print("\nSUCCESS: Received structured response.")
    else:
        print("\nFAILURE: Invalid response.")

if __name__ == "__main__":
    test_bidding_brain()
