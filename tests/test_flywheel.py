import requests
import json
import time

BASE_URL = "http://127.0.0.1:3005/react-py4web"
LOG_FILE = "logs/gemini_debug.log"
UNIQUE_REASON = "FLYWHEEL_VERIFICATION_REASON_XYZ"

def test_flywheel():
    print("1. Submitting Training Example...")
    example = {
        "contextHash": f"test-flywheel-{time.time()}",
        "gameState": json.dumps({
            "players": [{"name": "Me", "position": "Bottom", "hand": []}],
            "bid": {"type": "SUN", "suit": None},
            "phase": "Bidding"
        }),
        "badMove": "PASS",
        "correctMove": json.dumps({"action": "SUN"}),
        "reason": UNIQUE_REASON
    }
    
    # Correction: correctMove expects a string in the endpoint usually, but let's check.
    # The endpoint parses request.json.
    # 'correctMove' field in DB is TEXT.
    # In AIStudio, we send: correctMove: batchBid (string) or correctAction (string).
    # So passing a JSON string is correct.
    example["correctMove"] = json.dumps({"action": "SUN"})

    try:
        res = requests.post(f"{BASE_URL}/submit_training", json=example)
        if res.status_code != 200:
            print(f"Failed to submit: {res.text}")
            return
        print("   Submission Successful.")
    except Exception as e:
        print(f"   API Error: {e}")
        return

    print("2. Requesting Strategy (Triggering RAG)...")
    strategy_req = {
        "gameState": {
            "players": [{"name": "Me", "position": "Bottom", "hand": [{"rank": "A", "suit": "S"}]}],
            "bid": {"type": "SUN", "suit": None}, # Matches the example mode
            "phase": "Bidding"
        }
    }
    
    try:
        res = requests.post(f"{BASE_URL}/ask_strategy", json=strategy_req)
        print(f"   Response Code: {res.status_code}")
        # We don't care about the result, only the LOGS.
    except Exception as e:
        print(f"   API Error: {e}")

    print("3. Checking Logs for Injection...")
    time.sleep(1) # Wait for flush
    try:
        found = False
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            # Read last 100 lines maybe? Or all.
            lines = f.readlines()
            for line in lines[-50:]: # Check last 50 lines
                if UNIQUE_REASON in line:
                    found = True
                    break
        
        if found:
            print(f"SUCCESS: Found '{UNIQUE_REASON}' in logs. Flywheel is working!")
        else:
            print(f"FAILURE: Did not find '{UNIQUE_REASON}' in logs.")
            print("Tail of logs:")
            print("".join(lines[-10:]))
            
    except Exception as e:
        print(f"   Log Read Error: {e}")

if __name__ == "__main__":
    test_flywheel()
