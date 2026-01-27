---
description: Run Major System Verification (End-to-End Simulation with 4 Bots).
---

# Major System Verification

This workflow executes a comprehensive end-to-End test of the Baloot AI system. It simulates a full game environment to ensure stability, rule compliance, and server performance.

## 1. Quick Headless Logic Check
First, we run the internal logic simulation to catch any core engine crashes.
```powershell
python scripts/simulate_game.py
```

## 2. Full System E2E Simulation
This script connects 4 WebSocket clients to the running server, creates a room, and plays through a game.
**Prerequisite**: The server must be running (use `/WW`).

```powershell
python scripts/verification/verify_game_flow.py
```

> [!NOTE]
> If the Verify Game Flow script fails to connect, ensure the server is running on port 3005.
