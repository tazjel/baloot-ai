# ADR-0001: Adoption of Redis for Stateless Room Management

## Status
Accepted

## Context
The Baloot AI game server originally used an in-memory `RoomManager` (Python dictionary) to store game states. As the project scaled to support:
1.  **Multiple changes**: Frequent code reloads during development.
2.  **Scalability**: Potential for multiple worker processes.
3.  **AI Worker Separation**: The AI "Brain" runs in a separate process/worker and needs access to game state.

The in-memory approach caused state loss on server restarts, made it impossible to share state between the HTTP server and the AI worker, and created "zombie" rooms that persisted until reboot.

## Decision
We decided to direct **all game state storage to Redis** and make the `RoomManager` class **stateless**.

*   **State Store**: Redis (Key: `room:{id}`)
*   **Pub/Sub**: Redis (via `python-socketio` RedisManager) for event distribution.
*   **Persistence**: Redis RDB/AOF (configured in `docker-compose`).

## Consequences

### Positive
*   **Resilience**: The backend server can crash or restart without killing active games.
*   **Horizontally Scalable**: We can run multiple API servers behind a load balancer.
*   **Decoupling**: The AI Worker can independently fetch game state from Redis without querying the API server.
*   **Debuggability**: We can inspect the raw Redis state using tools or CLI to debug stuck games.

### Negative
*   **Serialization Overhead**: Every state update requires JSON serialization/deserialization.
*   **Complexity**: Requires a running Redis instance for development (added dependency).
*   **Race Conditions**: Potential for read-modify-write races if locking isn't handled (currently managed via optimistic handling or single-threaded event loop nature of `socketio`).

## Implementation Details
*   `RoomManager.get_room(id)` now fetches and deserializes from Redis.
*   `RoomManager.save_room(room)` serializes and saves to Redis.
*   Lobby listings use `KEYS "room:*"` (optimized later with sets).

## References
*   [python-socketio Redis Manager](https://python-socketio.readthedocs.io/en/latest/server.html#redis-manager)
