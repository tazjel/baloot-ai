import requests
import sys

# Testing configuration
BASE_URL = "http://localhost:3005"

def test_academy_api():
    print(f"Testing Academy API at {BASE_URL}...")
    
    # 1. Test List Puzzles
    print("\n[TEST] 1. GET /academy/puzzles")
    try:
        res = requests.get(f"{BASE_URL}/academy/puzzles")
        if res.status_code != 200:
            print(f"FAILED: Status {res.status_code}")
            return
        
        data = res.json()
        puzzles = data.get('puzzles', [])
        print(f"SUCCESS: Found {len(puzzles)} puzzles.")
        if len(puzzles) == 0:
            print("WARN: No puzzles found to test details.")
            return
            
        first_id = puzzles[0]['id']
        print(f"Targeting First Puzzle: {first_id}")
        
    except Exception as e:
        print(f"FATAL: Could not connect to server. Is it running? {e}")
        return

    # 2. Test Get Puzzle
    print(f"\n[TEST] 2. GET /academy/puzzles/{first_id}")
    try:
        res = requests.get(f"{BASE_URL}/academy/puzzles/{first_id}")
        if res.status_code != 200:
            print(f"FAILED: Status {res.status_code}")
            return
            
        puzzle_data = res.json().get('puzzle')
        if not puzzle_data:
             print("FAILED: No puzzle body returned")
             return
             
        title = puzzle_data.get('title')
        solution = puzzle_data.get('solution')
        print(f"SUCCESS: Loaded '{title}'")
        print(f"Expected Solution: {solution}")
        
    except Exception as e:
        print(f"FAILED: {e}")
        return

    # 3. Test Verify (Correct)
    print("\n[TEST] 3. POST /academy/verify (Correct Solution)")
    if solution['type'] == 'sequence':
        correct_moves = solution['data'] 
        
        try:
            payload = {"puzzleId": first_id, "moves": correct_moves}
            res = requests.post(f"{BASE_URL}/academy/verify", json=payload)
            result = res.json()
            
            if result.get('success'):
                print(f"SUCCESS: Server confirmed correct moves.")
            else:
                print(f"FAILED: Server rejected correct moves! Msg: {result.get('message')}")
        except Exception as e:
            print(f"FAILED: {e}")

    # 4. Test Verify (Incorrect)
    print("\n[TEST] 4. POST /academy/verify (Incorrect Solution)")
    try:
        bad_moves = ["2S"] # Playing a 2 of Spades (likely wrong for any puzzle)
        payload = {"puzzleId": first_id, "moves": bad_moves}
        res = requests.post(f"{BASE_URL}/academy/verify", json=payload)
        result = res.json()
        
        if not result.get('success'):
            print(f"SUCCESS: Server correctly rejected wrong moves. Msg: {result.get('message')}")
        else:
            print(f"FAILED: Server accepted wrong moves!")
    except Exception as e:
        print(f"FAILED: {e}")
        
    print("\nDone.")

if __name__ == "__main__":
    test_academy_api()
