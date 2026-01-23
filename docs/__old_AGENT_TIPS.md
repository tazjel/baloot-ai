# AGENT TIPS & GUIDE

## 🚀 Quick Start
- **Restart Server**: `./restart_server.ps1` (MANDATORY: Use this, never just `python run_game_server.py`)
- **Monitor Timer**: `Get-Content logs/timer_monitor.log -Tail 20 -Wait`
- **Check Debug Logs**: `Get-Content logs/server_debug.log -Tail 50`

## 📂 Key File Map
| Component | File Path | Description |
|-----------|-----------|-------------|
| **Timer Logic** | `game_engine/logic/timer_manager.py` | Centralized time tracking. |
| **Game Core** | `game_engine/logic/game.py` | Main game loop. See `check_timeout` & `auto_play_card`. |
| **Background** | `socket_handler.py` | `timer_background_task` runs here. |
| **Bot Brain** | `bot_agent.py` | `get_decision` is the entry point. |
| **Logs** | `logs/*.log` | `timer_monitor.log` (Hearts/Triggers), `server_debug.log` (General). |

## 🛠️ Debugging "Stuck Game" or "Delay"
If the user reports the game is stuck or AI is slow:
1.  **Check Heartbeats**: Read `logs/timer_monitor.log`. 
    - **Missing Heartbeats?** -> The Server Event Loop is BLOCKED. Search for synchronous DB calls or heavy loops.
    - **Heartbeats Present?** -> The Timer is running. Check for `Triggered` events.
2.  **Check Triggers**: 
    - **Triggered but No Action?** -> Logic failure. Check `server_manual.log` for Python errors.
    - **No Trigger?** -> Timer logic thinks time hasn't expired. Check `game.py` -> `check_timeout`.
3.  **Zombie Check**: Run `./restart_server.ps1` to kill orphaned processes.

## ⚠️ Pitfalls
- **Implicit Calls**: `bot_agent.load_experience` lazy-imports `common.py` which touches DB. This can be slow or crash in standalone scripts.
- **Logging**: Standard logging (`logging.info`) may be swallowed or misconfigured. Use `timer_monitor.log` or `server_manual.log` for definitive tracing.
- **Gevent**: The server runs on Gevent. **Avoid** blocking calls (like `time.sleep` or heavy `for` loops) in the main thread. Use `sio.sleep()` to yield.
