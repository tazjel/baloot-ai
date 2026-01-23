# Walkthrough: Screenshot-to-Scenario & Infrastructure Fixes

**Date:** 2026-01-18

## Overview
We successfully implemented the "Screenshot-to-Scenario" feature, allowing the AI Studio to ingest game state directly from images. We also resolved several critical infrastructure issues preventing the game stack from running smoothly.

## Key Changes

### 1. AI Studio: Screenshot Import
- **Frontend (`AIStudio.tsx`)**: Added file upload handler that sends images to the backend.
- **Backend (`controllers.py`)**: Created `/analyze_screenshot` endpoint.
- **AI Logic (`llm_client.py`)**: 
  - Switched to `gemini-flash-latest` model.
  - Added robust retry logic to handle API quota limits (429 errors).
    - *Verification*: Check `logs/gemini_debug.log` to see the actual prompt being sent with examples.
  - Prompt engineering to extract JSON game state from images.

### 2. Infrastructure Reliability
- **Redis**: Forced connection to `127.0.0.1` instead of `localhost` to prevent connection failures on Windows.
- **Server Routing**: Implemented WSGI middleware in `run_game_server.py` to correctly strip the `/react-py4web` URL prefix, ensuring the frontend can communicate with the backend API.
- **File Handling**: Fixed a crash in `controllers.py` by correctly accessing the file object from the `FileUpload` wrapper.

### 3. Magic Builder & Match Analysis
- *Debugging*: All inputs (user text, match json) and outputs (AI JSON) are logged to `logs/gemini_debug.log`. This is your black box recorder.
- *Endpoints*: `/generate_scenario` (for text) and `/analyze_match` (for history).

## Verification / How to Test
1. **Start the Stack**: Run the `/WW` workflow (Redis, AI Worker, Backend, Frontend).
2. **Open AI Studio**: Navigate to the "Scenario Builder" tab.
3. **Upload**: Click "Populate from Screenshot" and choose a game screenshot.
4. **Verify**: The board should fill with the correct cards, dealer position, and game phase.

## Known Issues
- Gemini usage is subject to free tier quotas; the retry logic handles this, but analysis may take a few seconds if retrying.

### 3. AI Studio: Real-time Assistant (New!)
- **Feature**: Added an "Ask AI Strategy" button in the Scenario Builder.
- **Functionality**: Sends the current board state to the Gemini AI to request the optimal move and strategic reasoning.
- **UI**: Displays the recommended move (Rank + Suit) and explanation directly in the sidebar, allowing one-click assignment as the "Correct Action".
### 4. Magic Builder (Text-to-Scenario)
- **Feature**: Natural language input to game state.
- **Functionality**: Users can type "Sun game, I have 4 Aces" and the AI will infer the rest of the board state.
- **Benefit**: Drastically reduces setup time for testing specific scenarios.

### 5. Automated Match Analysis
- **Feature**: Deep strategic critique of completed games.
- **Functionality**: Sends the full match history to Gemini to identify "Key Moments" where the team made a good move or a mistake.
- **Benefit**: Provides high-level coaching and helps identify patterns of error in bot play.

### 6. Candidate Flywheel (Automation Phase 1)
- **Headless Arena**: Implemented `game_engine/arena.py` which strips away networking and UI to run matches at **1000x real-time speed** (approx 1s per game).
- **The Scout**: Created `scripts/scout.py` to watch the arena's match logs and automatically identify "Losses" or interesting games to send to the AI for analysis.
- **Benefit**: This forms the foundation of our specific data generation pipeline. We can now generate thousands of games overnight.

## Session: Stability & Engineering Health (2026-01-22)

### 1. Frontend Stability Fixes
- **Root Cause**: A `TypeError` occurred when the `Card` component or `Table` rendering logic encountered `undefined` card objects (common during trick sweeping or fast-forwarding).
- **Fix**: 
  - Added defensive null checks in `Card.tsx` (Component now returns `null` safely).
  - Modified `Table.tsx` mapping logic for `tableCards` and `lastTrick.cards` to filter/skip undefined entries.
  - Enhanced `scanHandJS` to strictly filter valid cards before property access.

### 2. Strict Typing Refactor (Phase 4)
- **Goal**: Reduce reliance on `any` to prevent "Property of undefined" errors at compile time and improve IDE intellisense.
- **Changes**:
  - **`types.ts`**: Introduced `TableCardMetadata` and replaced `any` in `DetailedScore` and `GameState`.
  - **`gameLogic.ts`**: Fully typed the `tableCards` parameter across all utility functions.
  - **`trainingService.ts`**: Typed `askStrategy` and corrected API port alignment.
  - **`devLogger.ts`**: Switched from `any` to `unknown` for data payloads to force safer casting.

### 3. BiddingEngine Testing (Phase 4)
- **Goal**: Ensure the complex bidding logic (Gablak, Doubling Chains, Kawesh) is robust against regressions.
- **Changes**:
  - **`tests/test_bidding_engine_unit.py` [NEW]**: Added 13 targeted unit tests for `BiddingEngine` covering Phase transitions, SUN/HOKUM hierarchy, Gablak priority stealing, and the full doubling chain (Double -> Triple -> Four -> Gahwa).
  - **`tests/test_bidding_rules.py` [FIX]**: Updated existing integration tests to correctly sync `floor_card` and turn order with the new engine logic.
  - **Validation**: All tests pass, verifying complex rules like the "Sun Doubling Firewall" and "Antigravity Dealer Rotation" (Kawesh).

## Future Plans (Automation)
- **Voice Lines**: Audio integration for bot personalities.
- **Brain Dashboard**: UI to visualize learned Redis keys.
- **Regression Suite**: System to auto-convert "Match Analysis" mistakes into regression tests.
