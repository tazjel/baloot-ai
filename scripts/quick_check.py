import sys
import os
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description="Run quick targeted tests.")
    parser.add_argument('target', nargs='?', default='logic', help="Target module/test to run (e.g. 'logic', 'bidding', 'sawa')")
    args = parser.parse_args()

    base_cmd = ["python", "-m", "pytest"]
    
    # Map friendly names to test paths
    targets = {
        'logic': 'tests/test_game_logic.py',
        'bidding': 'tests/test_bidding_rules.py',
        'sawa': 'tests/test_scenarios.py -k sawa',
        'projects': 'tests/test_projects_logic.py',
        'all': 'tests/' 
    }
    
    # Default fallback to searching by keyword if not in map
    test_path = targets.get(args.target)
    
    if test_path:
        print(f"🚀 Running Quick Check for: {args.target} ({test_path})")
        cmd = base_cmd + test_path.split()
    else:
        # Assume it's a keyword match
        print(f"🔎 Searching tests for keyword: {args.target}")
        cmd = base_cmd + ["-k", args.target, "tests/"]

    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Quick Check PASSED")
    except subprocess.CalledProcessError:
        print("\n❌ Quick Check FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
