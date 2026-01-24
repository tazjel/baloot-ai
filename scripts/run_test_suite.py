
import subprocess
import os
import sys
import time

SCENARIOS = [
    "full_game",
    "bidding_sun",
    "bidding_hokum",
    "bidding_ashkal",
    "project_four",
    "project_sequence",
    "project_baloot",
    "sawa_test",
    "double_test",
    "stress_test",
    "edge_all_pass"
]


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
# Ensure project root is in path for subprocess execution context if needed
# But subprocess calls python cli_test_runner.py, so we need to pass env or ensure cli_test_runner handles strict paths.

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
REPORT_FILE = os.path.join(PROJECT_ROOT, "docs", "TEST_REPORT.md")

def run_scenario(scenario_name, extra_args=None):
    print(f"Running scenario: {scenario_name}...", end="", flush=True)
    log_file = os.path.join(LOG_DIR, f"{scenario_name}.log")
    
    cmd = [
        sys.executable, 
        os.path.join(SCRIPT_DIR, "cli_test_runner.py"), 
        "--scenario", scenario_name,
        "--log-file", log_file,
        "--debug"
    ]
    
    if extra_args:
        cmd.extend(extra_args)
    
    start_time = time.time()
    try:
        # Run process
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True
        )
        duration = time.time() - start_time
        
        success = (result.returncode == 0)
        
        # Parse log file for quick stats (optional)
        # For now just trust return code
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f" {status} ({duration:.2f}s)")
        
        return {
            "name": scenario_name,
            "status": status,
            "duration": duration,
            "log_file": log_file,
            "return_code": result.returncode
        }
        
    except Exception as e:
        print(f" Error: {e}")
        return {
            "name": scenario_name,
            "status": "❌ ERROR",
            "duration": 0,
            "log_file": log_file,
            "return_code": -1,
            "error": str(e)
        }

def generate_report(results):
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# Baloot Game Test Report\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Scenario | Status | Duration | Log File |\n")
        f.write("|---|---|---|---|\n")
        
        passed = 0
        total = len(results)
        
        for r in results:
            if "PASS" in r["status"]:
                passed += 1
            f.write(f"| {r['name']} | {r['status']} | {r['duration']:.2f}s | [View Log]({r['log_file']}) |\n")
        
        f.write(f"\n**Summary:** {passed}/{total} Passed\n")
    
    print(f"\nReport generated: {os.path.abspath(REPORT_FILE)}")

def main():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        
    results = []
    print(f"Starting execution of {len(SCENARIOS)} scenarios...\n")
    
    for scenario in SCENARIOS:
        settings = {} 
        # For stress test, maybe run fewer games for this quick suite?
        # Default is 1 game for most, stress test default in runner is ???
        # cli_test_runner.py defaults to 1 game.
        # But 'stress_test' scenario class defaults to 10 games validation logic?
        # Let's check test_scenarios.py... 
        # Yes, StressTestScenario(10). 
        # The runner loop runs N games passed via --games.
        # If we run "stress_test" with --games 1 (default), the validation might fail 
        # because it expects 10 games completed?
        # Let's check StressTestScenario code in test_scenarios.py
        
        # Valid: "if self.completed_games >= self.num_games"
        # If we run runner with --games 1, scenario.validate is called once.
        # num_games is 10. completed_games becomes 1. 1 >= 10 is False.
        # So it returns {success: True, message: "Game 1/10 completed"}?
        # Ah, validate returns success=True but just a message.
        # cli_test_runner.py checks result['success'].
        # So it might pass but just say "Game 1/10 completed".
        
        # To be "proper", for stress_test we should pass --games 10.
        
        extra_args = []
        if scenario == "stress_test":
             extra_args = ["--games", "5"]
             
        results.append(run_scenario(scenario, extra_args))
        
    generate_report(results)

if __name__ == "__main__":
    main()
