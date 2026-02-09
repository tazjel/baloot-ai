# Instructions for Claude: Improving Akka Logic in Baloot AI

**Context**: You are tasked with improving the "Akka" logic in the Baloot AI game engine. Akka in this codebase refers to a player claiming they have the "Boss" card (highest remaining card) of a specific suit in HOKUM mode.

**Objective**: Make the Akka logic robust, efficient, and bug-free.

## Constraints (CRITICAL)
- **IGNORE** `ai_worker/`, `visionary/`, `tools/`, and any machine learning components. Do not read them.
- **FOCUS ONLY** on:
    - `game_engine/logic/project_manager.py` (Core Logic)
    - `game_engine/logic/game.py` (State Delegation)
    - `frontend/src/components/ActionBar.tsx` (UI Trigger)
    - `frontend/src/utils/gameLogic.ts` (Frontend Validation)

## Current Implementation Status
- The backend logic resides in `ProjectManager.check_akka_eligibility` and `handle_akka`.
- A recent fix was applied to `check_akka_eligibility` to handle mixed card types (objects vs dicts) in `round_history` to prevent `KeyError: 'rank'`.
- The logic determines eligibility by checking if the player's highest card in a suit is strictly better than any *unplayed* card in that suit (excluding Aces, which are self-evident).

## Tasks for Improvement

1. **Refactor Card Tracking**:
    - The current method re-scans `round_history` every time to build the `played_cards` set. This is inefficient.
    - **Instruction**: optimization checking if `Game` class already maintains a `played_cards_registry` or logic `unplayed_cards` set and use that if available. If not, consider optimizing this scan or helper method.
    - **Robustness**: Ensure the card key generation (e.g. `f"{rank}{suit}"`) is consistent across the entire project (Backend and Frontend).

2. **Verify Rules**:
    - Review the logic:
        - Mode: HOKUM only? (Current: Yes)
        - Suit: Non-Trump only? (Current: Yes)
        - Rank: No Aces? (Current: Yes)
        - Condition: Must be highest *remaining* card?
    - **Action**: Confirm if these rules align with the user's expectation of "Akka" (or "Sira" depending on dialect). If you find ambiguities, add comments or TODOs.

3. **Frontend Synchronization**:
    - Check `frontend/src/components/ActionBar.tsx`. It uses `scanHandForAkka` from `utils/gameLogic`.
    - **Critical**: Ensure the frontend's local check (`scanHandForAkka`) matches the backend's strict check (`check_akka_eligibility`). If they drift, the button might appear but the action will fail (or vice versa).

4. **Error Handling**:
    - Ensure `handle_akka` gracefully handles cases where the state changes between the UI check and the server request (race conditions).

## Deliverables
- A refactored `ProjectManager` class with cleaner Akka methods.
- Sync updates to `frontend/src/utils/gameLogic.ts` if needed.
- No changes to unrelated AI/ML agents.
