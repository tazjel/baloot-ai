# Baloot AI & Game Engine ♠️

![Project Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![React](https://img.shields.io/badge/React-18-blue)
![Redis](https://img.shields.io/badge/Redis-Enabled-red)
![License](https://img.shields.io/badge/License-MIT-green)

A high-performance, multiplayer **Baloot** game engine featuring an advanced AI opponent ("The Brain"). This project combines traditional game rules with modern AI techniques (Reinforcement Learning & LLMs) to create a challenging and robust gaming experience.

## 🌟 Key Features

- **Hybrid AI System**:
  - **The Reflex**: Instant heuristic-based decision making for standard plays.
  - **The Brain**: Asynchronous Deep Learning/LLM-based strategy using Gemini & Redis.
- **Robust Multiplayer**: Resilient WebSocket architecture capable of handling disconnects and lag.
- **Data Flywheel**: Automatically records gameplay, analyzes mistakes (via "The Scout"), and trains the AI model.
- **AI Studio**: A dedicated dashboard for analyzing hands, debugging strategies, and replaying scenarios.
- **Premium UI**: Polished React frontend with animations, dark mode, and responsive design.

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **Docker Desktop** (for Redis)

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/baloot-ai.git
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
    python run_game_server.py
    ```

4.  **Start Frontend**
    ```bash
    cd frontend
    npm install
    npm start
    ```
    The game will be available at `http://localhost:3000`.

## 📚 Documentation

- **[Architecture Overview](docs/ARCHITECTURE.md)**: Logic separation, AI Flywheel, and Redis integration.
- **[Contributing Guide](CONTRIBUTING.md)**: Setup, testing, and code style.
- **[Game Rules](https://en.wikipedia.org/wiki/Baloot)**: Standard Baloot rules implementation details.

## 🛠️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Key for Google Gemini (AI Worker) | Required for Brain |
| `REDIS_HOST` | Redis Host address | `localhost` |
| `REDIS_PORT` | Redis Port | `6379` |

## 🤝 Contributing

We welcome contributions! Please check our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) for details.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Py4Web**: For the Python backend framework inspiration.

