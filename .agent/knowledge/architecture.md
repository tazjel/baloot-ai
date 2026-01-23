# System Architecture

## Overview
The application follows a **Client-Server** architecture using **WebSockets** for real-time state synchronization.

## 1. Backend (Python)
**Entry Point:** `run_game_server.py` -> `socket_handler.py`
**Core Logic:** `game_logic.py`

### Key Components
- **Socket Handler (`socket_handler.py`)**:
    - Manages `socketio.Server` (Async Mode: `gevent`).
    - **Events**:
        - `connect` / `disconnect`
        - `join_room` / `create_room`
        - `game_action`: The single funnel for all player moves (`BID`, `PLAY`, `DECLARE_PROJECT`, `SAWA`, `QAYD`, etc.).
    - **Bot Loop**: `bot_loop` runs as a background task to drive bot actions without blocking the main thread.
    - **Bot Agent (`bot_agent.py`)**:
        - **Heuristic Core**: Deterministic logic for Bidding (Sun/Hokum/Ashkal) and Playing.
        - **Memory System**: Tracks `played_cards` to optimize decisions (e.g., throwing points if partner winning).
        - **Sira Detection**: Evaluates hand for sequences to boost bidding confidence.

- **Game Engine (`game_logic.py`)**:
    - **`Game` Class**: The Source of Truth.
    - **State**: `phase` (BIDDING, PLAYING), `players` list, `table_cards`, `declarations`.
    - **Methods**:
        - `handle_bid(...)`: Updates `bid`, `trump_suit`, `game_mode`.
        - `play_card(...)`: Validates move, updates `table_cards`, resolves trick.
        - `get_game_state()`: Serializes the ENTIRE state to dict for frontend consumption.

- **Room Manager (`room_manager.py`)**: Singleton to map `roomId` -> `Game` instance.

## 2. Frontend (React + Vite)
**Entry Point:** `src/main.tsx` -> `App.tsx`
**State Management:** `useGameState` (Custom Hook).

### Key Components
- **`App.tsx`**: Main View Controller. Switches between `Lobby`, `Game`, `MultiplayerLobby`.
- **`useGameState.ts`**:
    - LISTENS to `game_update` events.
    - CALLS `socketService.emit('game_action')`.
    - Handles local sounds and UI-specific state.
- **`Table.tsx`**: Main game board renderer.
- **`SocketService.ts`**: Wrapper around `socket.io-client`.

## Data Flow
1. **User Action**: Click Card -> `handlePlayerAction` (Frontend) -> `socket.emit('game_action', {action: 'PLAY', ...})`.
2. **Server Processing**: `socket_handler.py` -> `game.play_card()`.
    - Validates move.
    - Updates State (Remove card from hand, add to table).
    - Checks for Trick End / Round End.
3. **Broadcast**: `game_update` event emitted with **Full Game State**.
4. **Client Update**: Frontend receives new state -> Re-renders `Table` and components.

## Testing Architecture
- **CLI Runner**: `cli_test_runner.py` bypasses the network layer to test `Game` logic directly.
- **Scenarios**: `test_scenarios.py` defines scripted game flows for automated validation.
