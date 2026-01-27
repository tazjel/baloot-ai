# Developer Tips & Tricks (Session Context)

## Critical Context (Session 2026-01-27)
- **Frontend Refactoring**: `WarRoomOverlay` has been extracted from `Table.tsx`. Future analytics features should be added there, not in `Table.tsx`.
- **Game Logic**: `Game.py` now has `calculate_win_probability()` and `increment_blunder()`. These use heuristic logic for now (MVP). Future work should connect `calculate_win_probability` to the MCTS engine for higher accuracy.
- **Professor Mode**: The `Professor` class in `ai_worker/professor.py` handles interventions. Currently, it uses a simple comparison between Human Move vs. Bot Move. It needs to be enhanced with true MCTS "Blunder Value" analysis.

## Workflow Shortcuts
- **Start Stack**: `python -m server.main` (Backend) + `npm run dev` (Frontend).
- **Verify Logic**: `python scripts/verification/verify_game_logic.py`.

## Gotchas
- **State Duplication**: `Table.tsx` is prone to state duplication (e.g., `selectedCardIndex` was duplicated). check `WarRoomOverlay` interactions carefully when adding new state.
- **Lint Errors**: `GameState` interface in `types.ts` must manually match the Python dictionary returned by `Game.get_game_state()`. Always update both when adding new state fields.

## Next Session Priorities
1. **YOLO Data Collection**: This was postponed. It's the next big AI innovation step.
2. **Professor MCTS**: Upgrade the `Professor` logic to use real value estimation delta.
