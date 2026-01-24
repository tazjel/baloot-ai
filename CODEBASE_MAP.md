# Baloot AI Codebase Map

## Directory Structure

### `ai_worker/`
**Purpose**: Contains the autonomous AI logic, including the Bot Agent and its memory.
- `agent.py`: Main `BotAgent` class (formerly `bot_agent.py`). Handles decision making, Redis interaction, and strategy delegation.
- `memory.py`: `CardMemory` class (formerly `bot_memory.py`). Tracks played cards, void suits, and partner signals.
- `dialogue_system.py`: Generates trash talk and dialogue using Gemini.
- `strategies/`: Specific bidding and playing strategies.

### `game_engine/`
**Purpose**: Core game logic independent of the web server.
- `logic/`
    - `game.py`: Main `Game` state machine.
    - `bidding_engine.py`: Handles the auction phase (Sun, Hokum, Gablak, etc.).
    - `trick_manager.py`: Handles trick resolution and validation.
    - `project_manager.py`: Handles declarations (Sira, Baloot, etc.).
    - `scoring_engine.py`: Calculates scores at end of round.
- `models/`: Data classes (Card, Deck, Constants).

### `server/`
**Purpose**: Web server infrastructure (Socket.IO, Flask/PyDAL).
- `socket_handler.py`: Entry point for WebSocket events. Delegates to `Game` and `BotAgent`.
- `room_manager.py`: Manages active game sessions.
- `models.py`: Database models (User, GameResult).
- `settings.py`: Configuration (Redis URL, etc.).

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
