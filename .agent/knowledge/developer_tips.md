
# Developer Tips & Lessons Learned

## 🚨 Critical Gotchas
1. **Frontend Port Mismatch**: 
   - The Frontend config (`config.ts`) defaults to port `8000` (Py4Web default), but our custom `server.main` runs on **Port 3005**.
   - **Always** verify `API_BASE_URL` points to `http://localhost:3005`.

2. **Server Startup**:
   - Use `restart_server.ps1` to cleanly kill zombies on port 3005.
   - If `restart_server.ps1` hangs, run `python -m server.main` manually to check for import errors.

3. **Data Integrity**:
   - When generating benchmarks (`generate_benchmark.py`), **VALIDATE** the data structure (e.g., player count). Raw data from `scout.py` might be incomplete if the simulation crashed.

## 🛠️ Useful Commands
- **Full Verification**: `pwsh scripts/verification/test_all_features.ps1` (if exists) or check `/workflows`.
- **Restart Stack**: `/restart` (Calls `restart_server.ps1`).
- **Check API**: `python scripts/check_puzzles_api.py`.

## 📁 Directory Notes
- `ai_worker/data` is the SOURCE of truth for training data. Do not use `backend/data`.
- `scripts/debugging` contains helpful scripts like `repro_crash.py`.

## 🧠 Cognitive AI (Phase 7)
1. **Refactoring Pattern**: Keeping `PlayingStrategy` (Heuristic) separate from `MCTSSolver` (Simulation) via `CognitiveOptimizer` (`ai_worker/cognitive.py`) prevented a huge mess. Maintain this separation.
2. **Memory Access**: `CardMemory` does **not** have `raw_state`. To access raw game data, use `ctx.raw_state` (BotContext) passed into methods.
3. **Simulation Performance**: `FastGame` runs at ~60,000 tricks/sec in Python. This is sufficient for MCTS (1000 iter/200ms). Do NOT rewrite in C++ unless latency budget drops below 50ms.
4. **Environment Hazard**: MCTS requires a valid, full-card environment. Using it in unit tests with 2-3 random cards will yield "garbage" answers (GIGO). Disable it for heuristic unit tests.
