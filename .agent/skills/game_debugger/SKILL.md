---
name: GameDebugger
description: Utilities for analyzing game logs to diagnose lag, crashes, and logic errors.
---

# GameDebugger Skill

This skill provides tools to analyze `server_debug.log` and `client_debug.log` to quickly identify performance bottlenecks (lag), crashes, and game state desynchronizations.

## Tools

### 1. Analyze Logs
**Script**: `scripts/analyze_logs.py`
**Usage**:
```bash
python .agent/skills/game_debugger/scripts/analyze_logs.py --file logs/server_debug.log
```
**Options**:
- `--file <path>`: Path to the log file (required).
- `--threshold <seconds>`: Threshold for "long pause" detection (default: 2.0s).

**What it does**:
- **Lag Detection**: Identifies time gaps between log entries larger than the threshold.
- **Error Extraction**: Prints summary of ERROR and WARNING lines.
- **Round Summary**: (Optional) Can summarize round starts/ends if logs contain standard markers.

## Workflow

1.  **Symptom**: User reports "The bot is delaying", "Game froze", or "I got kicked".
2.  **Action**: Run `analyze_logs.py` on `server_debug.log` and `client_debug.log`.
3.  **Analysis**:
    - Look for **"LONG PAUSE"** sections in the output. This indicates where the server or bot was stuck.
    - Look for **"Traceback"** or **"ERROR"** sections.
4.  **Fix**: Use the timestamp and context from the analysis to locate the code causing the issue.
