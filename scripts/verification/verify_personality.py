import sys
import os
import json

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.models.card import Card
from ai_worker.bot_context import BotContext
from ai_worker.strategies.bidding import BiddingStrategy
from ai_worker.personality import PROFILES

def test_personality():
    print("Testing Bot Personality...")
    
    # 1. Setup a Borderline Hand (Score ~16)
    # A (10) + Q (2) + some small cards
    # Sun Score Estimate:
    # A=10, Q=2 -> 12.
    # Length bonus? A, K, Q, J, 9 (Suit 1) -> Len 5. (5-3)*2 = 4. Total 16.
    # Aggressive (Bias +3): Threshold 18-3 = 15. 16 >= 15 -> BID.
    # Conservative (Bias -3): Threshold 18+3 = 21. 16 < 21 -> PASS.
    
    hand_cards = [
        {'rank': 'A', 'suit': 'H'}, # 10
        {'rank': 'Q', 'suit': 'H'}, # 2
        {'rank': '9', 'suit': 'H'},
        {'rank': '8', 'suit': 'H'},
        {'rank': '7', 'suit': 'H'}  # Length 5 -> +4
    ]
    # Total Score: 16
    
    # Mock State
    mock_state = {
        "players": [
            {"name": "Tester", "hand": hand_cards, "position": "Bottom"}
        ],
        "dealerIndex": 1, # Not dealer
        "phase": "BIDDING",
        "biddingRound": 1,
        "floorCard": None
    }
    
    strategy = BiddingStrategy()
    
    # 2. Test Conservative
    print("\n--- Testing CONSERVATIVE ---")
    ctx_safe = BotContext(mock_state, 0, personality=PROFILES['Conservative'])
    decision_safe = strategy.get_decision(ctx_safe)
    print(f"Decision: {decision_safe['action']} ({decision_safe.get('reasoning')})")
    
    # 3. Test Aggressive
    print("\n--- Testing AGGRESSIVE ---")
    ctx_risky = BotContext(mock_state, 0, personality=PROFILES['Aggressive'])
    decision_risky = strategy.get_decision(ctx_risky)
    print(f"Decision: {decision_risky['action']} ({decision_risky.get('reasoning')})")
    
    # 4. Assertions
    if decision_safe['action'] == 'PASS' and decision_risky['action'] in ['SUN', 'ASHKAL']:
        print("\n✅ SUCCESS: Personality Influenced Decision Correctly.")
    else:
        print("\n❌ FAILURE: Personalities did not behave as expected.")
        print(f"Expected Conservative=PASS, Aggressive=SUN or ASHKAL. Got Safe={decision_safe['action']}, Risky={decision_risky['action']}")


if __name__ == "__main__":
    test_personality()
