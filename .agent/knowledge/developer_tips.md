# Developer Tips & Tricks (Session Context)

## Critical Context (Session 2026-01-27) - MCTS Upgrade
- **MCTS Integrity**: We fixed the "AI Optimism Bug". The MCTS engine (`mcts.py`) now correctly uses adversarial selection (Minimax-style) during the Selection phase. Without this, the AI assumes opponents will play to help it win.
- **Simulation State**: We fixed the "Suit Identity Bug" in `utils.py`. The simulation generator MUST use `constants.SUITS` (♠, ♥, ♦, ♣) and NOT string literals ('S', 'H'...). Using the wrong symbols created duplicate cards in memory, breaking the simulation logic.
- **Professor Mode**: Now uses live MCTS analysis. Thresholds are set to 0.20 (Blunder) and 0.10 (Mistake).
- **Professor Debugging**: We added rigorous logging to `professor.py`. If you see "Illegal move" reports, grep `server_manual.log` for "PROFESSOR BUG".
- **Restart Logic**: `socket_handler.py` now explicitly handles `GAMEOVER` phase for "New Game" requests. Ensure any future Game Over logic respects this.

## Workflow Shortcuts
- **Start Stack**: `python -m server.main` (Backend) + `npm run dev` (Frontend).
- **Verify Logic**: `python scripts/verification/verify_game_logic.py`.
- **Verify Professor**: Use `game_engine/logic/game.py` locally or monitor `server_manual.log` for "Professor: Triggering Intervention".
- **Restart Game**: Use `/restart` slash command to cleanly reboot server and client.

## Gotchas
- **State Duplication**: `Table.tsx` is prone to state duplication. Check `WarRoomOverlay` interactions carefully.
- **Lint Errors**: `GameState` interface in `types.ts` must manually match the Python dictionary returned by `Game.get_game_state()`.
- **Card Identity**: `Card('S', '7')` is NOT equal to `Card('♠', '7')`. Always import `SUITS` from `constants.py`.

## Next Session Priorities
1. **YOLO Data Collection**: This is the next major initiative.
2. **Bot Personality Integration**: Connect the dialogue system to these new MCTS insights (e.g., bragging when `win_rate > 0.9`).

## Hybrid AI Architecture (Session 2026-01-28)
- **FastGame Encoding**: We implemented `FeatureExtractor.encode_fast()` to bypass object creation overhead. Use this when running MCTS simulations requiring neural inference.
- **Dependency Injection**: `MCTSSolver` now requires `neural_strategy` for PUCT. This is wired through `BotAgent` -> `PlayingStrategy` -> `CognitiveOptimizer`.

## Collaborative Signaling (Session 2026-01-28)
- **Source of Truth**: `collaborative_signaling_framework.md` is the master doc for all signal definitions.
- **Opposite Color Rule**: We implemented the advanced "Low Card = Opposite Color" signal. If debugging weird leads, check if `check_partner_signals` returned `PREFER_OPPOSITE`.
- **Testing**: Signaling logic is heavily unit tested in `tests/test_signals.py`.

- **Strategy Modes**: `BotAgent` now supports `heuristic`, `neural`, and `hybrid` modes per player via `game_state` config. Use this for A/B testing.

## Connection Management (Session 2026-01-28)
- **Redis Connections**: NEVER create new `redis.Redis()` connections inside high-frequency endpoints (like `get_ai_thoughts`). This exhausts file descriptors.
- **Shared Client**: Always use `server.common.redis_client`. It is initialized once and shared.
- **Symptom**: "Failed to fetch thoughts" or `Connection closed by server` usually means the backend is out of sockets.


## Py4Web / Bottle Integration (Session 2026-01-29)
- **Split Brain Issue**: When using `gevent` and custom runners (`main.py`), `py4web`'s auto-discovery (`bottle.default_app()`) can attach routes to the wrong instance.
- **Fix (Explicit Binding)**: Always pass the active `wsgi_app` to your controllers and manually bind routes:
  ```python
  def bind(app):
      app.route('/my/path', callback=my_func)
  ```
- **Static Files (404)**: `bottle.static_file` defaults the `root` to the current working directory of the *process*, not the file. Always calculate `PROJECT_ROOT` dynamically:
  ```python
  PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
  STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'static')
  ```
- **Vite Proxy**: Frontend Dev Server (5173) needs explicit proxy rules for `/static` to handle assets outside the SPA route.

## Visionary Studio AI (Session 2026-01-30)
- **Resolution Trap**: Training YOLO on full 1080p frames (resized to 640px) causes small cards to vanish. **Always train on ROIs (Crops)** that match the inference pipeline (e.g., Hand/Floor crops).
- **Auto-Labeling Config**: When using YOLO-World for auto-labeling full frames, use `imgsz=1280` and `conf=0.05` to ensure small objects are detected.
- **Data Pipeline**:
  1. `generate_roi_dataset.py` -> Extracts & Crops.
  2. `auto_label.py` -> Labels the crops.
  3. `train_visionary_yolo.py` -> Trains on the labeled crops.

## Stitch MCP Integration (Session 2026-01-31)
- **API Key & Refresh**: Stitch MCP works best with `X-Goog-Api-Key` instead of OAuth tokens in some contexts. After updating `mcp_config.json`, a **window reload/refresh** is often required for the IDE to re-handshake with the MCP server.
- **Projects**: Stitch Project IDs are persistent. Always document them (like in `visionary_studio.md`) since `list_projects` might fail if auth is flaky.

## Qayd Freeze Debugging (Session 2026-02-02)
- **Lock State Management**: When adding features that lock the game (e.g., Qayd investigations), ensure ALL timeout/auto-play paths respect `game.is_locked`. Use the `@requires_unlocked` decorator in `game.py`.
- **State Serialization**: Always serialize Card objects to dicts before storing in state that will be JSON-serialized. Use `card.to_dict()` or the new `game_engine/utils/serialization.py` helpers.
- **Dual State Bug**: Beware of multiple state objects for the same feature. The Qayd freeze was caused by `qayd_manager.state` vs `trick_manager.qayd_state` - only one was being updated.
- **Auto-Confirmation**: For Sherlock mode (bot-detected rule violations), implement auto-confirmation to prevent freeze waiting for manual input that bots can't provide.
- **Testing**: New integration tests in `tests/test_qayd_flow.py` cover the Qayd flow. Run them when modifying Qayd/lock logic.

## MCP Configuration (Session 2026-02-02)
- **Package Availability**: Before adding MCP servers to `mcp_config.json`, verify the npm package exists. `@modelcontextprotocol/server-git` does NOT exist (404).
- **Working Servers**: `stitch` (URL-based) and `filesystem` work reliably. Remove problematic servers to avoid blocking all MCP tools.

## Launch Logic & Agent Efficiency (Session 2026-02-02)
- **Headless Mode Pattern**: When launching servers for verification, ALWAYS use `-Headless` (if available) or redirect stdout/stderr to files. Capturing 200MB of log output in the agent's context window destroys token budget.
- **The "Missing Static" Crash**: Python servers (bottle/py4web) serving `index.html` must handle the *absence* of the build directory gracefully. Use `os.path.isfile()` checks and return 404 instead of crashing with `FileNotFoundError` or `ValueError: I/O operation on closed file`.
- **Readiness Probes**: Do NOT ping the root URL (`/`) for health checks if it serves a static file that might not exist. Create and use a dedicated minimal `/health` endpoint that returns a simple string ("OK").
- **Agent Directory Hygiene**: Keep `.agent/knowledge` lean. Large rulebooks (40KB+) should be moved to the Agent's Brain (artifacts) or Knowledge Base (KIs) to prevent them being loaded into every single session context. Use pointers in `.agent` to reference them.

