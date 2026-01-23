---
name: Automated Scout Management
description: Managing the Automated Scout, a system for batch game simulation and AI analysis.
---

# Automated Scout Management

The **Automated Scout** is a background process that simulates Baloot games, logs them, and uses Gemini to identify bot mistakes.

## 🛠️ Core Scripts

### 1. `scripts/run_nightly_scout.ps1` (The Orchestrator)
**Purpose**: The main entry point. It runs the simulation and then the analysis.
**Usage**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_nightly_scout.ps1
```
**Details**:
- Effectively runs `verify_game_flow.py` for 5 minutes (`--duration 300`).
- Then runs `scout.py`.

### 2. `scripts/verify_game_flow.py` (The Simulator)
**Purpose**: Connects 4 bots to the local server and plays random games to generate `logs/server_manual.log`.
**Usage**:
```bash
python scripts/verify_game_flow.py --duration 300
```
**Key Flags**:
- `--duration [seconds]`: How long to run the simulation (default 60). Use 300+ for full games.

### 3. `scripts/scout.py` (The Analyst)
**Purpose**: Parses `logs/server_manual.log`, identifies completed matches, and asks Gemini to find mistakes.
**Usage**:
```bash
python scripts/scout.py
```
**Outputs**:
- JSON files in `backend/data/training/` (e.g., `mistake_gameId_hash.json`).

## 🐞 Troubleshooting

### Log Files
- **Execution Log**: Stdout from the PowerShell script.
- **Game Events**: `logs/server_manual.log` (Look for `[EVENT]`).
- **Scout Log**: Stdout from `scout.py`.

### Common Issues
1.  **"Found 0 games"**:
    - The simulation didn't finish any rounds.
    - Check if `verify_game_flow.py` crashed or if the server is logging `[EVENT]`.
    - Ensure `game.py` has `log_event("ROUND_END", ...)` in `end_round`.

2.  **Simulation Disconnects Early**:
    - The server might be slow processing moves. Increase `--duration`.

3.  **BotContext Errors**:
    - If `scout.py` or the server crashes with `AttributeError: object has no attribute 'player_position'`, check `bot_agent.py`. It should use `ctx.position`.
