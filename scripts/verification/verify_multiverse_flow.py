import requests
import json
import sys
import time

BASE_URL = "http://localhost:3000"

def log(msg, color="white"):
    print(f"[{color.upper()}] {msg}")

def run_test():
    print("--- Verifying Multiverse Backend Logic ---")
    
    # 1. Get List
    try:
        resp = requests.get(f"{BASE_URL}/react-py4web/replay/list")
        if resp.status_code != 200:
            print(f"FAIL: List endpoint returned {resp.status_code}")
            return
        
        data = resp.json()
        matches = data.get('matches', [])
        if not matches:
            print("FAIL: No matches found to fork. Please play a game first.")
            return
            
        source_game = matches[0]
        source_id = source_game['gameId']
        print(f"PASS: Found source game {source_id}")
        
    except Exception as e:
        print(f"FAIL: Network error on list: {e}")
        return

    # 2. Fork Game
    print(f"Attempting to fork {source_id}...")
    try:
        payload = {
            "gameId": source_id,
            "roundNum": 1,
            "trickIndex": 3,
            "movesInTrick": 0
        }
        resp = requests.post(f"{BASE_URL}/react-py4web/replay/fork", json=payload)
        data = resp.json()
        
        if not data.get('success'):
            print(f"FAIL: Fork failed: {data}")
            return
            
        new_game_id = data.get('newGameId')
        print(f"PASS: Fork successful! New ID: {new_game_id}")
        
    except Exception as e:
        print(f"FAIL: Network error on fork: {e}")
        return

    # 3. Verify Tree (Multiverse)
    print("Checking Multiverse Tree for new node...")
    time.sleep(1) # Slight propagated delay
    try:
        resp = requests.get(f"{BASE_URL}/react-py4web/replay/multiverse")
        data = resp.json()
        nodes = data.get('nodes', [])
        
        # Check for new node
        found_node = next((n for n in nodes if n['id'] == new_game_id), None)
        
        if not found_node:
            print(f"FAIL: New game {new_game_id} NOT found in tree nodes.")
            print(f"Total nodes: {len(nodes)}")
            return
            
        print(f"PASS: Node found in tree.")
        print(f"Node Data: {json.dumps(found_node, indent=2)}")
        
        if found_node.get('parentId') or found_node.get('isFork'):
             print("PASS: Node correctly marked as Fork/Child.")
        else:
             print("WARNING: Node found but parentId might be missing (check logic).")
             
    except Exception as e:
        print(f"FAIL: Network error on multiverse: {e}")

if __name__ == "__main__":
    run_test()
