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
