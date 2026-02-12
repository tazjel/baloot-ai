# Baloot AI Codebase Map

## Directory Structure

### `ai_worker/`
**Purpose**: Contains the autonomous AI logic, including the Bot Agent and its memory.
- `agent.py`: Main `BotAgent` class. Handles decision making, Redis interaction, and strategy delegation.
- `memory.py`: `CardMemory` class. Tracks played cards, void suits, and partner signals.
- `dialogue_system.py`: Generates trash talk and dialogue using Gemini.
- `strategies/`: Specific bidding and playing strategies (heuristic-based).
- `signals/`: Collaborative Signaling Framework (Manager, Definitions, Emitter/Detector).
- `data/`: Training data and scout analysis results.
- `learning/`: Flywheel and data pipeline components.
- `mcts/`: Monte Carlo Tree Search solver.

### `game_engine/`
**Purpose**: Core game logic independent of the web server.
- `logic/`
    - `game.py`: Main `Game` state machine (facade controller).
    - `game_serializer.py`: JSON serialization/deserialization for Game state.
    - `bidding_engine.py`: Handles the auction phase (Sun, Hokum, Gablak, etc.).
    - `contract_handler.py`: Contract resolution and bid-result logic.
    - `doubling_handler.py`: Doubling/redoubling mechanics.
    - `trick_manager.py`: Handles trick resolution, validation, and Sawa logic.
    - `project_manager.py`: Handles declarations (Sira, Baloot, Akka, Sawa).
    - `scoring_engine.py`: Calculates scores at end of round.
    - `qayd_engine.py`: Qayd (Forensic Challenge) state machine.
    - `rules_validator.py`: Pure validation functions for move legality and violations.
    - `state_bridge.py`: Property aliases bridging `GameState` ↔ `Game` attributes.
    - `referee.py`: Rule enforcement and card comparison utilities.
    - `validation.py`: Move legality checker (is_move_legal).
    - `autopilot.py`: Auto-play logic (timeouts, bot fallback).
    - `timer_manager.py`: Turn timer and timeout management.
    - `phases/`: Phase-specific logic delegates.
        - `bidding_phase.py`: Bidding phase orchestration.
        - `playing_phase.py`: Playing phase orchestration.
        - `challenge_phase.py`: Qayd challenge phase handler.
    - `rules/`: Pure-function rule modules (sawa.py, akka.py, projects.py).
- `models/`: Data classes (Card, Deck, Constants).
- `core/`: State models (GameState, AkkaState, SawaState, Graveyard).

### `server/`
**Purpose**: Web server infrastructure (Socket.IO, Flask/PyDAL).
- `socket_handler.py`: Entry point for WebSocket events.
- `bot_orchestrator.py`: Manages bot turn orchestration and timing.
- `room_manager.py`: Manages active game sessions.
- `sherlock_scanner.py`: Background scanner for detecting illegal moves.
- `game_logger.py`: Structured game logging with ANSI colors.
- `handlers/`: Socket event handlers.
    - `game_lifecycle.py`: Game start, restart, end-round events.
    - `game_actions.py`: Bid, play, declare project events.
    - `room_lifecycle.py`: Room creation, join, leave events.
    - `timer.py`: Turn timer management.
- `routes/`: HTTP API routes (auth, qayd, brain, puzzles).
- `settings.py`: Configuration (Redis URL, etc.).
- `services/`: Service integrations (Gemini).

### `frontend/`
**Purpose**: React/Vite Frontend.
- `components/`: UI Components.
    - `Table.tsx`: Main game table container.
    - `ActionBar.tsx`: Player action panel (bid, play, declare).
    - `Card.tsx` / `CardVector.tsx`: Card rendering.
    - `HandFan.tsx`: Hand display with fan layout.
    - `DisputeModal.tsx`: Qayd dispute interface.
    - `GameToast.tsx`: Toast notification system.
    - `MatchReviewModal.tsx`: Post-match review screen.
    - `table/`: Sub-components (GameArena, TableHUD, PlayerAvatar, ScoreBadge, ContractIndicator, ProjectReveal, TurnTimer).
    - `dispute/`: Qayd sub-components (QaydMainMenu, QaydCardSelector, QaydFooter, QaydVerdictPanel).
- `services/`: API/Socket services, AccountingEngine, SoundManager, botService.
- `hooks/`: Custom hooks (useGameSocket, useGameState, useRoundManager, useGameRules, useBiddingLogic, usePlayingLogic, useActionDispatcher, useBotSpeech, useGameAudio, useGameToast, useGameTension, useLocalBot, useVoice).
- `utils/`: Helpers (gameLogic, scoringUtils, deckUtils, trickUtils, projectUtils, akkaUtils, animationUtils, sortUtils, devLogger).
- `types.ts`: Shared TypeScript interfaces (GameState, Player, Card, etc.).

### `scripts/`
**Purpose**: Organized into functional sub-folders.
- `launch/`: Server/stack management (launch_ww.ps1, restart_game.ps1, cleanup.ps1).
- `verification/`: Integration tests (verify_bidding_live.py, verify_qayd_live.py, etc.).
- `testing/`: Test runners & benchmarks (bot_iq_benchmark.py, cli_test_runner.py).
- `training/`: AI/ML training scripts (train_brain.py, generate_neural_data.py).
- `visionary/`: Visionary Studio tools (train_visionary_yolo.py, auto_label.py).
- `debug/`: Diagnostic scripts (debug_pickle.py, analyze_logs.py).
- `tools/`: Utility scripts (scout.py, lint.py, seed_puzzles.py).
- `archive/`: Superseded scripts.

### `tests/`
**Purpose**: Organized by domain.
- `bidding/`: Bidding engine tests.
- `game_logic/`: Core game mechanics, scoring, scenarios.
- `features/`: Feature tests (Akka, Ashkal, Kawesh, Sawa, Sira, Mashaari).
- `qayd/`: Qayd/forensic challenge tests.
- `bot/`: Bot/AI behavior tests.
- `server/`: Server, socket, rate limiter tests.
- `ai_features/`: Advanced AI (signaling, MCTS, professor, memory).
- `browser/`: Playwright browser tests.
- `unit/`: Isolated unit tests.

### `docs/`
**Purpose**: Project documentation.
- `ARCHITECTURE.md`, `BALOOT_RULES.md`, `FRONTEND_GUIDE.md`: Active references.
- `archive/`: Historical reports (missions, bug fixes, code reviews).
- `archive/claude/`: AI assistant instructions (archived).

### `ai_training/`
**Purpose**: RL training environment (PPO agent, ONNX export).

### `tools/dashboard/`
**Purpose**: Streamlit dashboard for monitoring.

## Key Flows

### Bot Decision Flow
1. `server/socket_handler.py` → `bot_loop()` triggers `bot_agent.get_decision()`.
2. `ai_worker/agent.py` → Delegates to `bidding_strategy` / `playing_strategy`.
3. Returns action to `socket_handler.py`, which calls `game.handle_bid()` or `game.play_card()`.

### Bidding Flow
1. User action `BID` → `game.handle_bid()`.
2. `game.py` → delegates to `bidding_engine.process_bid()`.
3. `bidding_engine.py` validates rules (Gablak, etc.) and updates `ContractState`.
4. `game.py` syncs state via `_sync_bid_state()` (for frontend/bot visibility).
