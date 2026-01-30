# Baloot AI Codebase Map

## Directory Structure

### `ai_worker/`
**Purpose**: Contains the autonomous AI logic, including the Bot Agent and its memory.
- `agent.py`: Main `BotAgent` class (formerly `bot_agent.py`). Handles decision making, Redis interaction, and strategy delegation.
- `memory.py`: `CardMemory` class (formerly `bot_memory.py`). Tracks played cards, void suits, and partner signals.
- `dialogue_system.py`: Generates trash talk and dialogue using Gemini.
- `strategies/`: Specific bidding and playing strategies.
- `signals/`: Collaborative Signaling Framework (Manager, Definitions, Emitter/Detector).
- `data/`: Training data and scout analysis results (formerly `backend/data`).
- `visionary/`: (See `game_engine/visionary`)

### `dataset/`
**Purpose**: YOLOv8 Training Data.
- `images/`: Training and Validation images (train/val).
- `labels/`: YOLO-format labels (txt) (train/val).
- `data.yaml`: YOLOv8 Configuration file.

### `models/`
**Purpose**: Trained ML Models.
- `yolo_v8n_baloot.pt`: Fine-tuned YOLOv8 Nano model for card recognition.

### `game_engine/`
**Purpose**: Core game logic independent of the web server.
- `logic/`
    - `game.py`: Main `Game` state machine.
    - `bidding_engine.py`: Handles the auction phase (Sun, Hokum, Gablak, etc.).
    - `trick_manager.py`: Handles trick resolution and validation.
    - `project_manager.py`: Handles declarations (Sira, Baloot, etc.).
    - `project_manager.py`: Handles declarations (Sira, Baloot, etc.).
    - `scoring_engine.py`: Calculates scores at end of round.
- `models/`: Data classes (Card, Deck, Constants).
- `visionary/`: **Visionary Studio** Core.
    - `visionary.py`: `VisionaryProcessor` (Frames), `CardRecognizer` (YOLO), `DatasetGenerator`.

### `server/`
**Purpose**: Web server infrastructure (Socket.IO, Flask/PyDAL).
- `socket_handler.py`: Entry point for WebSocket events. Delegates to `Game` and `BotAgent`.
- `room_manager.py`: Manages active game sessions.
- `models.py`: Database models (User, GameResult).
- `settings.py`: Configuration (Redis URL, etc.).

### `archive/`
**Purpose**: Legacy code and scripts.
- `legacy_server_node/`: Archived Node.js server.
- `legacy_server_node/`: Archived Node.js server.
- `legacy_patch.py`, `old_test_game_phases.py`: Archived scripts.

### `scripts/`
Refactored intofunctional groups:
- `verification/`: Integration tests (`verify_game_flow.py`, `verify_ai_client.py`).
- `visionary/`: **Visionary Studio Tools** (`train_visionary_yolo.py`, `auto_label.py`, `generate_roi_dataset.py`, `test_visionary.py`).
- `debugging/`: Tools for symptom analysis (`repro_crash.py`, `debug_screenshot.py`, `debug_yolo_prediction.py`).
- Root: Workflow entry points (`run_nightly_scout.ps1`, `restart_server.ps1`).

### `frontend/`
**Purpose**: React/Vite Frontend.
- `components/`: UI Components (Card, Table, Hand).
- `services/`: API and Socket services.
- `hooks/`: Custom React hooks (useGame, useSound).

## Key Flows

### Bot Decision Flow
1. `server/socket_handler.py` -> `bot_loop()` triggers `bot_agent.get_decision()`.
2. `ai_worker/agent.py` -> Checks `redis` for "Brain" overrides or delegates to `bidding_strategy` / `playing_strategy`.
3. Returns action to `socket_handler.py`, which calls `game.handle_bid()` or `game.play_card()`.

### Bidding Flow
1. User action `BID` -> `game.handle_bid()`.
2. `game.py` -> delegates to `bidding_engine.process_bid()`.
3. `bidding_engine.py` validates rules (Gablak, etc.) and updates `ContractState`.
4. `game.py` syncs state via `_sync_bid_state()` (for frontend/bot visibility).
