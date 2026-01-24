# Contributing to Baloot AI

First off, thanks for taking the time to contribute! 🎉
The following is a set of guidelines for contributing to Baloot AI. These are just guidelines, not rules. Use your best judgment and feel free to propose changes to this document.

## 🛠️ Development Setup

### Backend (Python)
1.  Ensure Python 3.10+ is installed.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run tests to verify setup: `pytest`

### Frontend (React)
1.  Navigate to `frontend/`: `cd frontend`
2.  Install packages: `npm install`
3.  Start development server: `npm start`

### Infrastructure (Redis)
We use Redis for AI caching and task queues. The easiest way to run it is via Docker:
`docker-compose up -d redis`

## 🧪 Testing Policy
We prioritize stability and correctness, especially for Game Logic.

- **Unit Tests**: Required for any change to `server/`, `game_engine/`, or `ai_worker/`.
- **Command**: Run `pytest` from the root directory.
- **Specific Suites**:
  - `tests/test_game_logic.py`: Core game rules.
  - `tests/test_bidding_engine.py`: Bidding & Doubling logic.
  - `tests/test_scoring_comprehensive.py`: Point calculation verification.

## 🎨 Code Style

### Python
- **Style Guide**: PEP 8.
- **Formatter**: We recommend using `Black`.
- **Typing**: Use type hints (`from typing import ...`) for all new function definitions.

### TypeScript / React
- **Linter**: ESLint (Standard config).
- **Naming**: PascalCase for Components, camelCase for functions/vars.

## 📝 Pull Request Process

1.  **Issue**: Ensure there is an open issue describing the problem or feature.
2.  **Branch**: Create a branch off `main` with a descriptive name (e.g., `fix/bidding-timeout`).
3.  **Changes**: Make your changes. Keep commits atomic and messages clear (Imperative mood: "Fix bug" not "Fixed bug").
4.  **Tests**: Add or update tests. Ensure all tests pass.
5.  **Review**: Open a PR. Fill out the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md).

## 🐛 Bug Reports

Scan the [Issue Tracker](https://github.com/yourusername/baloot-ai/issues) before submitting.
If you find a new bug, please use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md) and include:
- Steps to reproduce
- Expected vs. Actual behavior
- Logs or Screenshots

## ⚖️ License
By contributing, you agree that your contributions will be licensed under the MIT License.
