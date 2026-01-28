# Project Status

## Overview
**Baloot Web Game** - A multiplayer implementation of the Saudi card game Baloot using React (Frontend) and Python (Backend) with Socket.IO.

## Features Checklist

### Agent Knowledge Base
- **[Decision Log](decision_log.md)**: Conceptual & Architectural decisions.
- **[Tech Debt](tech_debt.md)**: Known issues and refactoring wish-list.
- **[UI Standards](ui_standards.md)**: Design system & component rules.
- **[Architecture](architecture.md)**: System design & data flow.
- **[Glossary](glossary.md)**: Domain terminology.

### Core Gameplay
- [x] **Deck & Defaulters**: Standard 32-card deck, shuffling, dealing (3+2).
- [x] **Bidding Phase**:
    - [x] Sun & Hokum bidding.
    - [x] Second round bidding restrictions.
    - [x] Floor card revealing & assigning.
    - [x] **Ashkal** (Dealer/Partner special bid).
    - [x] **Kawesh** (Redeal request for point-less hands).
    - [x] **Doubling**: Basic implementation (`doubling_level`).
- [x] **Playing Phase**:
    - [x] Turn-based card playing.
    - [x] Trick resolution (Standard rules).
    - [x] **Akka Declaration**: Highest remaining card UI & Sound. (Implemented: Hokum Only, Strict Rules)
    - [x] **Projects (Mashrou)**: 
        - [x] Detection (Sira, 50, 100, 400, Baloot).
        - [x] Declaration & Comparison (Winner-takes-all).
        - [x] Reveal Animation.
    - [x] **Sawa (Sawa)**:
        - [x] Claim & Response Logic.
        - [x] Challenge Mechanics (Khasara on failure).
    - [x] **Qayd (Penalty)**: 
        - [x] Basic State (`qayd_state`).
        - [x] Full implementation (Frontend connected to Backend).

### AI & Bots
- [x] **Bot Agents**: 
    - [x] **Smart Heuristic Strategy**:
        - [x] **Bidding**: Sun/Hokum Strength detection + Project (Sira/50) awareness.
        - [x] **Playing**: Context-aware (Lead Strong, Cut weak, Support Partner).
        - [x] **Memory**: Tracks played cards to calculate probabilities.
        - [x] **Phase 3 Awareness**:
            - [x] **Master Cards**: Knows highest remaining card.
            - [x] **Void Detection**: Avoids getting cut by tracking opponent voids.
            - [x] **Endgame Solver**: "All Masters" optimization to run the table.
    - [x] **UI Insights**: Real-time reasoning display ("AI Analysis 🧠") in Sidebar.
    - [x] **Background Loop**: Automatic playing.
    - [x] **Crash Resilience**: Fixed infinite loops.
    - [x] **Auto-Play on Timeout**:
        - [x] Backend Timer Logic (0.1s resolution).
        - [x] Frontend Settings Sync.
        - [x] Wrapper for Bot Logic (Human Auto-Play).
- [x] **IntelligentBot AI (Offline/Client-Side)**:
    - [x] **Architecture**: RLCard (Python) -> ONNX (Export) -> onnxruntime-web (Frontend).
    - [x] **Environment**: Custom `BalootEnv` wrapping game logic.
    - [x] **Training**: NFSP Agent trained via Self-Play (Pilot verified).
    - [x] **Inference**: Browser-based inference using `.onnx` model (Zero Server Cost).


### System & Infrastructure
- [x] **Networking**: Socket.IO event-driven architecture.
- [x] **Room Management**: Create/Join/Add Bot.
- [x] **Error Handling**: Graceful recovery, timeouts, auto-restart.
- [x] **Testing**: CLI Test Runner with extensive scenarios.
- [x] **Agent Configuration**: Optimized MCP tools and workflows for efficiency.

### UI/UX
- [x] **Lobby**: Name entry, Game start.
- [x] **Game Table**:
    - [x] Hand Fan view (Responsive).
    - [x] Floor Card display.
    - [x] Player Avatars.
- [x] **Modals**:
    - [x] Round Results (ExternalApp style).
    - [x] Dispute/Challenge.
    - [x] Store/Settings/Emotes.

### Scoring & Logic
- [x] **Hokum Scoring Engine**:
    - [x] Strict 162-point rule (152 cards + 10 Earth).
    - [x] **Kaboot**: 25 points (Hokum), 44 points (Sun).
    - [x] **Khasara**: Buyer loses if raw score < 81 (Tie at 81).
    - [x] **Jabor Rounding**: Strict rounding (down if <= 5, up if > 5).
    - [x] **Earth Bonus**: Separated logic for Last Trick (10 points).

## Known Issues / Active Tasks
- **[FIXED] Auto-Play Freeze / Bot Lag**: Resolved by disabling client-side timer enforcement and implementing server-side emergency rescue in `bot_loop`.
- **[FIXED] TypeError (reading 'us')**: Added safe defaults for `matchScores` in `Table.tsx`.
- **[FIXED] Visual Feedback**: Added "Sending..." indicator to prevent double-actions.
- **Qayd System**: Integrated Frontend to Backend. Logic pending further rule refinements if any.
- **Bot Intelligence**: Improved (Phase 2 Heuristics Logic Implemented - Sira/Memory).
- **Mobile Responsiveness**: Hand fan overlap issues were recently addressed but need monitoring on smaller screens.

## Recent Fixes
- **Unified Scoring System (Abnat)**: Refactored backend scoring to use a raw "Abnat" system for all game modes, ensuring consistent calculation before game point conversion (Sun/Hokum formulas). Fixed Project values (e.g., 400 Project = 200 Abnat).
- **Timer UI Overhaul**: Implemented a "Kamelna-style" circular countdown timer:
    - **Visuals**: Thick Gold/Green/Red ring attached to the active player's avatar.
    - **Countdown**: Large, shadowed number for high visibility.
    - **Integration**: Attached to a dedicated "Me" avatar in the bottom-right.
- [x] **Bug Fix**: Resolved `NameError` in `end_round` (game_logic.py) that caused game to freeze/crash at end of trick/round.
- [x] **Visual Fix**: Restored "Me" Avatar and fixed Z-Index/Rendering issues for Countdown Timer to ensure visibility.
- [x] **Logic Fix**: Corrected component shadowing issue in `Table.tsx` where old internal components were overriding the new fixed ones.
- [x] **Code Cleanup**: Removed massive accidental code duplication in `Table.tsx` to fix syntax errors.
- [x] **Logic Fix**: Corrected `isCurrentTurn` Logic in `Table.tsx` to use dynamic player indices, ensuring Timer appears on correct avatar.
- [x] **Performance**: Reduced Bot Delay (0.5s -> 0.05s) and Optimized `get_game_state` payload size.
- [x] **UI**: Separated Countdown Number into a distinct bubble.
- [x] **Critical Fix**: Resolved "Failed to fetch thoughts" crash by implementing shared Redis client in `server/common.py` (Fixed Connection Leak).
- [ ] **Verification**: Monitor for any further freezes during gameplay.
- **UI Cleanup**: Removed clutter based on user feedback:
    - Deleted card count stacks from avatars.
    - Removed Top-Right icons (Settings/Store).
    - Removed the "Me" avatar (and implicitly the timer attached to it) per user request (User is aware timer is gone).
- **Round Results UI**: Refined UI to match "Kamelna" style (RTL, Detailed Columns).
- **Akka & Projects**: Strict rules implemented and verified.
- **Refactoring**: `game.py` logic split into `TrickManager` and `ProjectManager`. Shared constants adopted across Server and Bot.

- **Goal**: Verify Game Integrity and Scoring.
- **Status**:
    - [x] **Verification**: Ran full backend simulation (Passed).
    - [x] **Frontend Tests**: Fixed Akka/Ace test case (Passed).
    - [x] **Scoring Tests**: Verified Sun/Hokum points, Kaboot, and Doubling logic (Passed).
- **Next**: Logic Fix: Solve the rounding in Hokom to calculate the score the right way.
- **Note**: AI endpoints are currently disabled in `controllers.py` as the legacy `ai_worker` was removed.

## Critical Infrastructure Updates (Debugging Session)
**Port Conflict Resolution & Stability Fixes:**
- **Backend Port Moved**: Moved Python Game Server to **Port 3005** to resolve persistent conflicts with Zombie processes on 3000-3003.
- **Direct Connection**: Frontend now connects **Directly** to `http://localhost:3005`, bypassing the unreliable Vite Proxy.
- **Crash Fixes**:
    - **Recursion/Hooks**: Fixed Infinite Loop/Crash in `Table.tsx` caused by conditional hooks.
    - **WASM/ONNX**: Temporarily disabled client-side AI (`IntelligentBot`) to prevent `wasm streaming compile failed` crash.
- **Telemetry**: Implemented Remote Telemetry Logging to debug client-side issues without console access.
