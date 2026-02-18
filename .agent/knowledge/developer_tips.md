# Developer Tips & Tricks

## Critical Gotchas
- **Card Identity**: `Card('S', '7')` is NOT equal to `Card('♠', '7')`. Always import `SUITS` from `constants.py`.
- **MCTS Integrity**: MCTS engine uses adversarial selection (Minimax-style). Without this, the AI assumes opponents help it win ("AI Optimism Bug").
- **Simulation State**: Simulation generator MUST use `constants.SUITS` (♠, ♥, ♦, ♣) and NOT string literals ('S', 'H'...). Using wrong symbols creates duplicate cards ("Suit Identity Bug").
- **Redis Connections**: NEVER create new `redis.Redis()` inside high-frequency endpoints. Always use `server.common.redis_client`.
- **State Serialization**: Always serialize Card objects to dicts before JSON-serializable state. Use `card.to_dict()`.
- **Dual State Bug**: When adding features with state (e.g., Qayd), ensure only ONE state object exists. Multiple state copies cause desync.

## Workflow Shortcuts
- **Start Stack**: `python -m server.main` (Backend) + `npm run dev` (Frontend)
- **Verify Logic**: `python scripts/verification/verify_game_logic.py`
- **Restart Game**: Use `/restart` or `/start` workflow to cleanly reboot server + client
- **Headless Mode**: When launching servers for verification, use `-Headless` or redirect output. Capturing logs in agent context destroys token budget.

## Architecture Notes
- **BotAgent Modes**: Supports `heuristic`, `neural`, and `hybrid` modes per player via `game_state` config.
- **Signaling Framework**: `collaborative_signaling_framework.md` is the master doc. "Low Card = Opposite Color" signal implemented.
- **Professor Mode**: Uses live MCTS analysis. Thresholds: 0.20 (Blunder), 0.10 (Mistake).
- **Game Serialization**: `game_serializer.py` handles pickle-safe Redis persistence. Custom `__getstate__`/`__setstate__` on Game object.
- **FastGame**: `FeatureExtractor.encode_fast()` bypasses object overhead for MCTS neural inference.

## Server & Integration
- **Health Checks**: Use `/health` endpoint, NOT root `/`. Root serves static files that may not exist.
- **Static Files**: `bottle.static_file` defaults root to CWD. Always calculate `PROJECT_ROOT` dynamically.
- **Vite Proxy**: Frontend dev server (5173) needs explicit proxy rules for `/static`.
- **Lock State**: Features that lock the game must respect `game.is_locked`. Use `@requires_unlocked` decorator.

## Flutter & Dart
- **State Management**: Riverpod with `StateNotifier` pattern in `mobile/lib/state/`.
- **Static Analysis**: Use `mcp_dart_analyze_files` for deep code analysis instead of regex grepping.
- **Widget Inspection**: `mcp_dart_get_widget_tree` fetches runtime UI hierarchy (requires `connect_dart_tooling_daemon`).
- **Auto-Fixes**: `mcp_dart_dart_fix` / `dart fix --apply` resolves bulk lint errors.
- **Tests**: ~130 Flutter tests in `mobile/test/`. Run with `flutter test`.

## Agent Protocols
- **Signature Rule**: Always sign your model name at the end of statements. Example: `[Antigravity]`.
- **Status Board**: `.agent/knowledge/agent_status.md` — check at session start, update when starting/completing work.
- **File Locks**: `.agent/knowledge/file_locks.md` prevents multi-agent conflicts.
- **Directory Hygiene**: Keep `.agent/knowledge` lean. Large docs go to Agent Brain (KIs/artifacts).
