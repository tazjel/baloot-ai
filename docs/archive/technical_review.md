# Baloot AI Technical Review & Roadmap (Phase 2)

## Executive Summary
Following the "Stability Sprint", the Baloot AI codebase requires a strategic shift from monolithic scripts to a modular, domain-driven architecture. This report outlines the plan to refactor core logic, harden process management, and enhance the dashboard for forensic debugging.

---

## 1. Refactoring & Organization

### 1.1. Problem Identification
*   **Monolithic Files:** `game_engine/logic/game.py` and `ai_worker/agent.py` currently violate the Single Responsibility Principle, mixing business logic, state mutation, and I/O (Redis/Network).
*   **Coupling:** Game rules are intertwined with the loop mechanism, making it difficult to test specific scenarios (e.g., specific Qayd calculations) without spinning up a full game.

### 1.2. Proposed Module Structure
We propose separating **Pure Domain Logic** from **Infrastructure/State Management**.

#### **Game Engine Refactoring**
Refactor `game_engine/logic/game.py` into a package `game_engine/core`:

| Module | Responsibility | Type |
| :--- | :--- | :--- |
| `state.py` | Data definitions (`GameState`, `Player`, `Deck`). Pydantic models recommended. | **Pure Data** |
| `rules.py` | Validations (`is_valid_move`), Scoring (`calculate_trick_score`), and Win conditions. | **Pure Functions** |
| `mechanics.py` | State transitions (`play_card(state, card) -> NewState`). | **Pure Functions** |
| `service.py` | The "Controller". Handles Redis streams, calls `mechanics`, persists state. | **Impure/IO** |

#### **AI Worker Refactoring**
Refactor `ai_worker/agent.py` to decouple the "Brain" from the "Body":

| Module | Responsibility |
| :--- | :--- |
| `transport/redis_adapter.py` | Handles subscription to game channels and writing commands. |
| `strategies/` | Pluggable strategies (e.g., `MCTS`, `Heuristic`, `RL_Model`). |
| `brain.py` | Selects the strategy and computes the move given a `GameState`. |

---

## 2. Critical Aspect Management

### 2.1. Addressing "Ghost Code" (Zombie Processes)
Ghost processes occur when workers crash or hang without releasing resources or updating their status.

**Recommendations:**
1.  **Supervisor Pattern:** Do not run scripts directly (e.g., `python agent.py`). Use a process manager like `supervisord` or `Docker` entrypoints with health checks.
2.  **Active Heartbeats:** 
    *   Every worker must write to a Redis key `worker:health:<id>` every 5 seconds (TTL 10s).
    *   **The Reaper:** A separate service monitoring these keys. If a key expires, the Reaper flags the worker as DOWN and triggers an alert or restart logic.
3.  **Graceful Shutdown:** Implement `signal` handlers (`SIGINT`, `SIGTERM`) to finish the current computation and close Redis connections cleanly.

### 2.2. Solving Redis State Desync
Desync happens when the in-memory state of a worker diverges from Redis, usually due to race conditions or missed updates.

**Recommendations:**
1.  **Single Writer Principle:** Only the **Game Engine Service** is allowed to *write* to the authoritative `GameState` in Redis. AI Agents are *Read-Only* consumers.
2.  **Optimistic Concurrency Control (CAS):** 
    *   Use Redis `WATCH` on the game key before writing updates.
    *   If the key changes during calculation, abort and retry with the fresh state.
3.  **Event Sourcing (Lite):** Instead of just overwriting state, append the *Action* to a Redis Stream. The Game Engine consumes the stream to produce the state. This ensures strict ordering.

---

## 3. Dashboard & Live Inspection (v3.1+)

### 3.1. Live Inspector Enhancements
To move beyond basic modularity:

*   **Timeline / Playback:** 
    *   Record every state change as a "Delta" in a separate Redis List/Stream.
    *   Add a **Seek Bar** in the dashboard to replay the game tick-by-tick.
*   **State Diffing:** 
    *   When stepping through the timeline, highlight the specific fields that changed (e.g., `current_player: "North" -> "East"`).

### 3.2. The 'Qayd War Room'
For debugging complex scoring logic (Qayd):

*   **Logic Tracing:** 
    *   Instrument `rules.py` to return a "Trace Object" alongside the result.
    *   *Example:* `Result: 152 Points (Trace: Base=100 + Project=50 + Bonus=2)`.
    *   Display this breakdown in the dashboard when inspecting a score.
*   **Sandbox Simulation:**
    *   "What if" mode: Allow developers to take a live game state, clone it into a local sandbox within the dashboard, and try different moves to see how the logic reacts without affecting the live game.
