# Server Package 🖥️

This directory contains the Python backend code for the Baloot game server.

## Key Components

- **`socket_handler.py`**: The core event listener for Socket.IO. Handles all real-time game events (`join_game`, `make_bid`, `play_card`).
- **`room_manager.py`**: Manages active game instances.
- **`controllers.py`**: py4web HTTP controllers for REST API endpoints (e.g., specific game data queries).
- **`models.py`**: Database definitions (py4web DAL).
- **`game_logic.py`**: A facade that re-exports `game_engine` components for legacy compatibility.
- **`logging_utils.py`**: Centralized logging configuration.

## Circular Dependency Warning ⚠️

**Do NOT import `room_manager` in `__init__.py`!**
The `room_manager` imports `game_logic`, which imports `game_engine`, which imports `trick_manager`, which imports `logging_utils` (which is in `server` package). If `__init__.py` imports `room_manager`, this cycle crashes the server.

Explicitly import `room_manager` only where needed (e.g., inside functions or in `run_game_server.py`).
