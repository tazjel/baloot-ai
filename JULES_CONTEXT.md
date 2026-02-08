# Jules Context & Instructions for Baloot AI

**Project Name**: Baloot AI
**Stack**: Python (Backend), React/Vite (Frontend), Redis (State/Message Bus)

## ❌ CRITICAL ANTI-PATTERNS (DO NOT DO THIS)
1.  **NO New Top-Level Packages**: Do **NOT** create a package named `baloot_ai`. The project root is the python source root.
2.  **NO Parallel Logic**: Do **NOT** re-implement `ProjectManager` or `Game`. Use the existing classes in `game_engine/`.
3.  **NO Magic Imports**: Do not assume `baloot_ai.game_engine` exists. Use `game_engine.logic...`.

## 📂 Architecture Map
*   **`game_engine/`**: The Source of Truth.
    *   `logic/game.py`: The Coordinator (State Machine).
    *   `logic/project_manager.py`: Handles Declarations (Sra, Baloot). **Akka is handled here too.**
    *   `logic/phases/`: Distinct phase logic (e.g., `bidding_phase.py`, `challenge_phase.py` for Qayd).
*   **`ai_worker/`**: The Bot Brains.
    *   `agent.py`: The `BotAgent`.
    *   `strategies/`: Neural/Heuristic decision logic.
*   **`server/`**: The Connectivity Layer.
    *   `main.py`: Entry point.
    *   `socket_handler.py`: WebSocket events.

## 📖 Domain Dictionary
*   **Akka** (aka "The Boss"): A declaration in **Hokum** mode that you hold the highest *remaining* card in a suit. It is **NOT** a standard "Project" like Sra, but handled by `ProjectManager.handle_akka`.
*   **Sawa** ("Equal"): A request to end the round because hands are equal or the winner is determined.
*   **Qayd** ("Foul/Challenge"): A Forensic Challenge where a player accuses another of a rule violation (Revoke, Renege, Wrong Bid). Logic lives in `ChallengePhase`.

## 🛠️ Working with this Codebase
1.  **Search First**: Before implementing `Project`, check `game_engine/logic/project_manager.py`. It likely exists.
2.  **State is Sacred**: The `Game` state is serialized to Redis. Do not store state in local variables that aren't persisted to `self.game`.
3.  **Use the Tools**: Use `grep_search` to find where `handle_akka` or `check_sawa` are defined.

## 🤖 Bot Logic Guidelines
*   **Bot Identity**: Bots are instances of `BotAgent` in `ai_worker/agent.py`.
*   **Memory**: Bots use `CardMemory` to track played cards.
*   **Cheating**: Bots must **NOT** cheat unless explicitly configured for "Professor Mode" (Analysis). Standard bots must respect hidden information.
