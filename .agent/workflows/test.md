---
description: Run the game test suite
---

This workflow runs the CLI-based test runner to verify game logic.

1. **Run Full Game Scenario**
   Runs a complete simulated game from start to finish.
   // turbo
   ```powershell
   python cli_test_runner.py --scenario full_game --verbose
   ```

2. **Run Interactive Mode**
   Start the interactive CLI where you control one player against bots.
   // turbo
   ```powershell
   python cli_test_runner.py --interactive
   ```

3. **Run Stress Test**
   Run 10 quick games to check for crashes.
   // turbo
   python cli_test_runner.py --scenario stress_test --games 10 --quiet
   ```

4. **Run Verified Bot Scenarios**
   Runs the new refactored bot logic verification suite.
   // turbo
   ```powershell
   python tests/test_bot_scenarios.py
   ```
