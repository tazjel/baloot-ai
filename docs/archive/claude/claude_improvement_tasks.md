# Mission Log: High-Impact Codebase Upgrades for Claude

*Copy these tasks one by one and paste them into Claude to execute.*

---

## ✅ Mission 1: The "Big Split" (Frontend Architecture) [COMPLETED]

**Context**: `useGameState.ts` has become a "God Object" (800+ lines). It handles sockets, audio, game logic, and useGameState state, leading to massive re-renders and race conditions.
*(Refactoring complete. Split into `useGameSocket`, `useGameAudio`, `useLocalBot`, and `useGameState`.)*

---

## ✅ Mission 2: Brain Surgery (AI Logic Decoupling) [COMPLETED]

**Context**: `QaydEngine` (`qayd_engine.py`) currently contains `_bot_auto_accuse`.
*(Refactoring complete. Extracted bot logic to `ForensicScanner` in `ai_worker/strategies/components/forensics.py`.)*

---

## ✅ Mission 3: Law & Order (Validator Extraction) [COMPLETED]

**Context**: `QaydEngine` mixed state management with rule validation.
*(Refactoring complete. Created `RulesValidator` in `game_engine/logic/rules_validator.py` and updated `QaydEngine` to delegate validation.)*

---

## ✅ Mission 4: Speed Demon (React Performance) [COMPLETED]

**Context**: `Table.tsx` and `useGameState` forced re-renders.
*(Refactoring complete. Created `RapidStore` for high-frequency state, isolated timers/cursors, and memoized components. Re-renders <16ms confirmed.)*

---

## 🛡️ Mission 5: The "Safe Guard" (Crash Recovery)

**Context**: If the WebSocket drops or a state update fails, the user is stuck. We need a "Self-Healing" mechanism.

**Prompt for Claude:**
> "Implement a 'State Reconciliation' system in `frontend/src/hooks/useGameSocket.ts`.
> 1.  **Sequence Numbers**: Add a `seq_id` to every backend state emission.
> 2.  **Detection**: If the frontend receives `seq_id: 5` after `seq_id: 3`, it detects a gap.
> 3.  **Recovery**: Automatically request a `FULL_STATE_SYNC` from the backend to fill the gap.
> 4.  **UI**: Show a subtle 'Reconnecting...' amber pulse, but do not block interaction if possible."

---


---

## ✅ Mission 6: The "Grand Consolidation" (UI Debt) [COMPLETED]

**Context**: The roadmap highlighted massive fragmentation in Card components.
*(Completed via `Card.tsx` consolidation. Replaced `CardVector`, `CardReal`, `CardV2` with a unified generic `Card` component.)*

---

## 📈 Mission 7: The "Ladder" (Progression Engine)

**Context**: The `app_user` table has a `league_points` field that is dead code. We need an ELO-based progression system to retain players (Roadmap Section 2.2).

**Prompt for Claude:**
> "Implement the Player Progression System in `server/services/progression_service.py`.
> 1.  **ELO Engine**: Create a function `calculate_post_match_elo(team_a_avg, team_b_avg, result)` using standard ELO formulas.
> 2.  **Tier Logic**: Implement `get_tier_from_points(points)` (Bronze: 0-800, Silver: 800-1200, etc.).
> 3.  **Integration**: Update `game_logger.py` to call this service when a game finishes (`GamePhase.GAMEOVER`), updating the `league_points` in the DB.
> 4.  **API**: Add a simple endpoint via `controllers.py` to fetch `GET /api/leaderboard/top100`."

---

## 🤝 Mission 8: The "matchmaker" (Queue Logic)

**Context**: Currently, we only have manual room creation. To complete against "source platform", we need an instant "Play Now" button (Roadmap Section 2.1).

**Prompt for Claude:**
> "Implement a Matchmaking Queue in `server/services/matchmaker.py`.
> 1.  **Queue Structure**: Use a Redis List `matchmaking_queue` to hold waiting player IDs.
> 2.  **Worker Loop**: Create a background task that runs every 5 seconds:
>     - Pops 4 players from the queue.
>     - Checks if their ELOs are within a 400-point spread (simple bucket matching).
>     - Calls `room_manager.create_room()` and emits `MATCH_FOUND` to those 4 sockets.
> 3.  **Timeout**: If a player waits >30s, match them with 3 Bots immediately."

---

## ✅ Mission 9: The "Type Police" (Strict TypeScript) [COMPLETED]

**Context**: The codebase had loose typing in critical areas (`QaydState`).
*(Refactoring complete. Replaced `any` with strict `CardModel` unions in `types.ts` and updated consumers like `QaydOverlay.tsx`.)*

*Use these missions to drive significant architectural quality into the project.*
