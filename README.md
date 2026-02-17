# Baloot AI & Game Engine ♠️

![Project Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-19-blue)
![Redis](https://img.shields.io/badge/Redis-Enabled-red)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Tests-535_passing-brightgreen)

A high-performance, multiplayer **Baloot** game engine featuring an advanced AI opponent ("The Brain"). This project combines traditional game rules with modern AI techniques (Reinforcement Learning & LLMs) to create a challenging and robust gaming experience.

## 🌟 Key Features

- **Hybrid AI System**:
  - **The Reflex**: Instant heuristic-based decision making for standard plays.
  - **The Brain**: Reinforcement Learning system that learns from game logs via Redis.
  - **The Scout**: Automated daily analysis tool that uses LLMs (Gemini) to find mistakes and generate training data.
- **Voice & Trash Talk**: Dynamic, personality-driven AI dialogue system. Bots speak in Arabic (Hejazi/Najdi dialects) using Text-to-Speech!
  - *Khalid (Aggressive)*, *Saad (Balanced)*, *Abu Fahad (Conservative)*.
- **Robust Multiplayer**: Resilient WebSocket architecture capable of handling disconnects and lag.
- **"The Professor" Mode 🎓**: Real-time AI Coach that interrupts the game when you make a strategic blunder, explaining the mistake and offering a better move.
- **War Room Dashboard 📉**: Live analytics showing Win Probability graphs and Blunder Heatmaps during gameplay.
- **AI Studio**: A dedicated dashboard for analyzing hands, debugging strategies, and replaying scenarios.
- **Premium UI**: Polished React frontend with `framer-motion` physics-based animations, glassmorphism design, and interactive feedback.

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Docker Desktop** (for Redis, optional — set `OFFLINE_MODE=true` to play without it)

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/tazjel/baloot-ai.git
    cd baloot-ai
    ```

2.  **Environment Setup**
    Copy the example environment file and add your API keys (for AI features).
    ```bash
    cp .env.example .env
    # Edit .env and add your GEMINI_API_KEY
    ```

3.  **Start Infrastructure & Backend**
    ```powershell
    # Start Redis
    docker-compose up -d redis

    # Install Python Dependencies
    pip install -r requirements.txt

    # Run Game Server
    python -m server.main
    ```

    **Pro Tip**: If you are on Windows, use the `/WW` slash command (or run `workflow_scripts/ww.ps1`) to launch everything at once!

4.  **Start Frontend**
    ```bash
    cd frontend
    npm install
    npm start
    ```
    The game will be available at `http://localhost:3000`.

## 📂 Project Structure

- **`game_engine/`**: Pure Python game state machine (Pydantic models, trick resolution, scoring).
- **`ai_worker/`**: AI strategy layer — 31 modular strategy components, brain cascade, empirical thresholds from 109 pro games.
- **`server/`**: FastAPI/WebSocket backend (room management, auth, real-time multiplayer).
- **`frontend/`**: React 19 + TypeScript UI (Vite, Framer Motion animations).
- **`tests/`**: 535+ tests covering game logic, AI strategies, and scoring validation.
- **`docs/`**: Architecture, rules, and contributing guides.
- **`scripts/`**: Development, data mining, and testing utilities.

## 📚 Documentation

- **[Architecture Overview](docs/ARCHITECTURE.md)**: Logic separation, AI Flywheel, and Redis integration.
- **[Frontend Guide](docs/FRONTEND_GUIDE.md)**: Architecture, State Management, and UI Systems.
- **[Contributing Guide](docs/CONTRIBUTING.md)**: Setup, testing, and code style.
- **[Codebase Map](CODEBASE_MAP.md)**: Master index for AI Agents.
- **[Game Rules](https://en.wikipedia.org/wiki/Baloot)**: Standard Baloot rules implementation details.

## 🛠️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis Host address | `localhost` |
| `REDIS_PORT` | Redis Port | `6379` |
| `OFFLINE_MODE` | Play without Redis | `false` |

## 🤝 Contributing

We welcome contributions! Please check our [Contributing Guide](docs/CONTRIBUTING.md) and [Code of Conduct](docs/CODE_OF_CONDUCT.md) for details.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Py4Web**: For the Python backend framework inspiration.

