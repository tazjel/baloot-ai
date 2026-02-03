# Codebase Map

## High-Level Structure

- **ai_worker/**: The AI "Brain" (Sherlock/MCTS).
  - `agent.py`: Main AI entry point.
  - `mcts/`: Monte Carlo Tree Search implementation.
  - `memory.py`: Redis-based memory.
- **frontend/**: React + Vite application.
  - `src/`: Source code (Components, Pages, Hooks).
  - `src/components/`: Reusable UI components.
  - `src/pages/`: Route handlers.
  - `src/services/`: API and Socket communication.
- **game_engine/**: Core Python logic.
  - `logic/game.py`: The Game State Machine (Refactored).
  - `logic/phases/`: Phase implementations (Bidding, Playing, Challenge).
  - `logic/trick_manager.py`: Trick rules and flow.
  - `models/`: Data classes (Card, Player, Deck).
- **server/**: Flask + Socket.IO Backend.
  - `app.py`: Server entry point.
  - `controllers.py`: HTTP routes.
  - `socket_handler.py`: Real-time event handling.
- **tests/**: Unit and Integration tests.

## Key Mechanisms
- **Phase State Pattern**: `Game` delegates to `phases/` modules based on `self.phase`.
- **Qayd (Forensic Mode)**: Handled by `ChallengePhase` + `QaydManager`.
- **AI Worker**: Runs as a separate process, communicating via Redis/Socket.IO.
