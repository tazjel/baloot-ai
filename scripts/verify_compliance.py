import subprocess
import sys
import os

def run_command(command, description):
    print(f"\n>>> Running: {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"PASSED: {description}")
            return True, result.stdout
        else:
            print(f"FAILED: {description}")
            print(result.stderr or result.stdout)
            return False, result.stdout
    except Exception as e:
        print(f"ERROR: Could not run {description}: {str(e)}")
        return False, str(e)

def main():
    print("="*60)
    print("      BALOOT CORE RULE COMPLIANCE REPORT      ")
    print("="*60)

    checks = [
        {
            "cmd": "pytest tests/test_bidding_rules.py tests/test_projects_logic.py tests/test_scoring_comprehensive.py",
            "desc": "Unit Tests: Bidding & Scoring Rules"
        },
        {
            "cmd": "python run_test_suite.py",
            "desc": "Scenario Simulations: Full Game Flow"
        }
    ]

    results = []
    if all_passed:
        print("COMPLIANCE VERIFIED: All core rules match standard Baloot rules.")
    else:
        print("COMPLIANCE WARNING: Some rules may deviate from standards. See logs above.")
    print("="*60)

if __name__ == "__main__":
    main()
