import os
import json
import glob
import sys

def verify_puzzles():
    # Adjust path to find server directory
    # Script is in scripts/, so up one level
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    puzzle_dir = os.path.join(base_dir, 'server', 'content', 'puzzles')
    
    print(f"Scanning {puzzle_dir}...")
    
    files = glob.glob(os.path.join(puzzle_dir, "*.json"))
    if not files:
        print("No puzzles found!")
        sys.exit(1)
        
    print(f"Found {len(files)} puzzles.")
    
    errors = 0
    for fpath in files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check required fields
            required = ['id', 'title', 'description', 'difficulty', 'initial_state', 'solution']
            missing = [k for k in required if k not in data]
            
            if missing:
                print(f"[FAIL] {fname}: Missing fields {missing}")
                errors += 1
                continue
                
            # Check ID matches filename
            expected_id = fname.replace('.json', '')
            if data['id'] != expected_id:
                print(f"[WARN] {fname}: ID '{data['id']}' does not match filename '{expected_id}'")
            
            # Check Initial State
            state = data['initial_state']
            if 'players' not in state or 'currentTurn' not in state:
                print(f"[FAIL] {fname}: initial_state missing players/currentTurn")
                errors += 1
                continue
                
            print(f"[PASS] {fname} - {data['title']}")
            
        except json.JSONDecodeError:
            print(f"[FAIL] {fname}: Invalid JSON")
            errors += 1
        except Exception as e:
            print(f"[FAIL] {fname}: {e}")
            errors += 1
            
    if errors > 0:
        print(f"\nVerification Failed with {errors} errors.")
        sys.exit(1)
    else:
        print("\nAll puzzles verified successfully!")

if __name__ == "__main__":
    verify_puzzles()
