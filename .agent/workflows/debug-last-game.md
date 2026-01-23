---
description: Analyze the log of the most recently played game for errors and lag.
---

This workflow automatically finds the latest log file in `logs/` and runs the analyzer on it.

1. Analyze Latest Log
// turbo
```bash
python .agent/skills/game_debugger/scripts/analyze_logs.py --latest
```
