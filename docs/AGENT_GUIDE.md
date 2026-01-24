# Agent Guide 🤖

**For**: AI Agents (Gemini, Claude, GPT) and Human Developers.
**Purpose**: How to navigate, debug, and improve this specific codebase without breaking things.

## 🚨 Critical Rules (The "Prime Directives")

1.  **Always use `restart_server.ps1`**:
    - *Why*: The Python server spawns child processes that standard CTRL+C often misses on Windows.
    - *Command*: `./restart_server.ps1` (located in root).
    - *Consequence*: If you don't, you'll see "Address already in use" or zombie bots playing in the background.

2.  **Monitor the Heartbeat**:
    - *Why*: The game loop runs on Gevent. If a single function blocks (e.g., `time.sleep(5)` instead of `sio.sleep(5)`), the entire server freezes.
    - *Command*: `Get-Content logs/timer_monitor.log -Tail 20 -Wait`
    - *Sign of Health*: You should see `[HEARTBEAT]` every 1 second. If it stops, you blocked the loop.

3.  **Respect the Architecture**:
    - *Frontend*: React + Context API. Do not add Redux unless explicitly asked.
    - *Backend*: Flask + Socket.IO (Gevent).
    - *AI*: Hybrid (Reflex = Redis, Brain = Async Worker).

## 🛠️ Common Workflows

### 1. "The Game is Stuck!" Debugging
**Symptom**: Players can't play cards, timer is frozen.
**Steps**:
1.  **Check Heartbeat**: Is `timer_monitor.log` updating?
    - *No*: You blocked the thread. Search for large `for` loops or `requests.get` calls in the critical path.
    - *Yes*: The timer is running, but logic failed.
2.  **Check Triggers**: Look for `[TIMER_TRIGGERED]` in logs.
    - *Present*: The timer fired, but the `handle_timeout` function crashed or bailed out. Check `server_manual.log` for Python exceptions.
    - *Absent*: `game.check_timeout()` thinks it's not time yet. Check `game.timer_start_time` vs `now()`.

### 2. Adding a New Bot Feature
1.  **Modify `BotContext`**: Ensure you have the data you need.
2.  **Update Strategy**: Edit `ai_worker` strategies (do not bloat `bot_agent.py` further).
3.  **Test**: Run `pytest tests/test_bot_strategy.py`.

## 📂 File Map
| Path | Purpose |
|------|---------|
| `run_game_server.py` | Entry point. |
| `game_engine/logic/timer_manager.py` | The "Heart" of the timing system. |
| `game_engine/logic/trick_manager.py` | Handles trick resolution and card validation. |
| `game_engine/logic/project_manager.py` | Handles project declarations and scoring. |
| `bot_agent.py` | The "Reflex" bot logic (Uses shared strategies in `ai_worker/strategies`). |
| `logs/timer_monitor.log` | **Most important log file**. Tracks loop health. |

## 🧠 AI Studio & Data Flywheel
1.  **Native Video Analysis**:
    - *Task Warning*: Do NOT try to implement frame-by-frame extraction in the frontend. Gemini 1.5 Flash now supports native video uploads via the `analyze_video` method in `GeminiClient`.
    - *MIME Types*: The backend is sensitive to MIME types. If an upload fails, check `controllers.py` mimetype mapping.
2.  **Data Flywheel (RAG)**:
    - *How it works*: User corrections in the "Scenario Builder" are saved to `db.bot_training_data`. 
    - *Injection*: When the AI is asked for strategy (`ask_strategy`), the backend retrieves matching scenarios and injects them as **Few-Shot Examples** into the prompt.
    - *Verification*: Check `logs/gemini_debug.log` to see the actual prompt being sent with examples.
    - **NOTE**: AI features are currently **DISABLED** in `controllers.py` awaiting a new `ai_worker` implementation. Endpoints will return "AI Service Disabled".

## 🚀 Efficiency Tips for Next Agent
- **Avoid Repeating Verification**: Check `tests/test_flywheel.py` and `tests/test_video_analysis.py` before re-implementing logic.
- **Backend Reloads**: `py4web` reloads `controllers.py` on save, but it might NOT reload `ai_worker/llm_client.py` unless the server is restarted. Use `./restart_server.ps1` if your LLM changes aren't taking effect.
- **Redis Inspection**: If AI "thoughts" aren't showing up, use `redis-cli KEYS "bot:thought:*"` to see if the worker is actually producing output.
- **Port 3005**: The primary entry point is Port 3005. Port 8000 is legacy.
- **Slash Commands**: Use `/WW` (Window Worker) to launch the full stack. It handles Redis, Backend, Frontend, and AI Worker in one go.
- **Voice Debugging**: If bots aren't speaking, check `logs/server_manual.log` for `[DIALOGUE]` tags. Ensure your volume is up and the browser has permission to play audio.

## 🧪 Testing Guidelines
- **Integration Tests**: `tests/test_scenarios.py` runs full simulated games.
- **Flywheel Test**: `tests/test_flywheel.py` verifies the RAG-lite pipeline.
- **AI Studio**: Use "Populate from Screenshot" or "Analyze Full Video" in the Studio tab.

## 🤝 Handover & Survival Guide (Read Me First!)
*Tips from the previous agent to help you survive and thrive.*

### 1. Don't Guess, Grep!
- **Bad (Terminal)**: `grep "foo" . -r` (Fails on Windows!)
- **Good (Tool)**: Use the `grep_search` tool! It works everywhere.
- **Good (Terminal)**: If you MUST use the terminal, use `findstr` (CMD) or `Select-String` (PowerShell).
- **Why**: The codebase is modular. Finding is faster than assuming, but `grep` is not native to Windows. Always use the provided *tools* first.

### 2. Verify Infrastructure Before Coding
- **Redis Check**: Before implementing Redis features, run `python scripts/test_redis.py`. If it hangs, Docker is likely blocking the port.
- **Restarting**: Use `./restart_server.ps1` for the backend. Use `docker-compose restart redis` for DB. If ports are blocked, find the PID occupying standard ports (5000, 3000, 6379) and kill them.

### 3. Model Compatibility (Gemini)
- **Don't Assume Models**: `gemini-1.5-flash` might not be available in the installed SDK version.
- **Check First**: Run `python scripts/list_models.py` to see exactly what strings are valid (e.g., `gemini-2.0-flash`, `gemini-pro`).
- **Quota**: If `scout.py` hits 429 errors, it means the free tier quota is full. The script saves partial progress, so just wait and retry.

### 4. The Candidate Flywheel (Automated Scout)
- **Automated Routine**: Run `powershell -ExecutionPolicy Bypass -File scripts/run_nightly_scout.ps1`.
  - *What it does*: Runs a 5-minute game simulation (`verify_game_flow.py`) then triggers the Scout analysis (`scout.py`).
- **Generating Data (Manual)**: Run `python scripts/verify_game_flow.py --duration 300` to generate logs without running analysis.
- **Finding Mistakes**: Run `python scripts/scout.py` to analyze existing `logs/server_manual.log`.
- **Training Brain**: Run `python scripts/train_brain.py` (Offline Learning) - *Pending implementation of full consumtion pipeline*.
- **Brain Override**: The bot (`bot_agent.py`) automatically checks Redis. If you suspect it's ignoring the brain, check `logs/server_manual.log` for `[THE BRAIN]` tags.

### 5. Common Pitfalls & Fixes
- **BotContext Attributes**: Be careful! The `BotContext` class uses `ctx.position` (not `ctx.player_position`). This caused a silent crash previously. ALWAYS check `ai_worker/bot_context.py` definition.
- **Socket Handler Blocking**: NEVER put `time.sleep()` or file writes inside `socket_handler.py` functions like `handle_sawa_responses`. It will block the Websocket heartbeat. Use `sio.sleep()` and `logger`.
- **PowerShell Popups**: The `restart_game.ps1` script now runs processes in `-WindowStyle Hidden`. If you need to see the console output, check the log files (`server_manual.log`, `server_debug.log`) instead of looking for a window.
- **Frontend Undefined Props**: Accessing properties like `.rank` on a specialized `Card` object can crash the app if the object is undefined/null. Always add safety checks (`if (!card) return null;`) in React components, especially within `map` loops.
- **Circular Dependency Trap**: The `server` package and `game_engine` often import each other (e.g., `trick_manager` -> `server.logging_utils` -> `server.room_manager` -> `game_logic` -> `game_engine`). **Always** use `scripts/diagnose_imports.py` after structural changes to verify you haven't created a hidden cycle that only appears during import time.
- **Frontend Animations**: We use `framer-motion` exclusively. Do not write complex CSS keyframes manually; use the `motion.div` wrapper component.
- **Test Before Commit**: Due to complex imports, `pytest` is your best friend. Run `pytest tests/test_bidding_engine.py` (or relevant test) *before* marking a task complete.
- **Engine State Sync in Tests**: When writing unit tests for stateful components like `BiddingEngine`, remember to manually sync `floor_card` and `phase` if you are injecting them directly into the engine instance, as the engine doesn't automatically pull from the parent `Game` object in isolated unit tests. See `tests/test_bidding_rules.py` for examples of advancing turns before testing priority-based actions like Ashkal.
