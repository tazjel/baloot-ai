# AGENT_README: Project Knowledge Base

**Welcome, Agent.**
This document serves as your onboarding guide to the Baloot AI Project (React-Py4Web). Use this to orient yourself quickly and work efficiently.

## 🧠 Core Capabilities
The project is a Multiplayer Baloot Game with an advanced "AI Studio" for training bots.

1.  **AI Studio (`/react-py4web`)**:
    *   **Builder Mode**: Manually create or edit game scenarios.
    *   **Training Mode**: Interactive logic puzzles for humans (Lichess-style).
    *   **Bidding Mode**: Batch generator for 5-card bidding scenarios.
    *   **Perception**: "Import from Video" and "Populate from Screenshot" using Gemini 1.5 Flash.
    *   **Data Flywheel**: Every saved scenario also saves the source image to `uploads/dataset/` for future YOLO training.

2.  **Game Server (`run_game_server.py`)**:
    *   Uses `py4web` + `python-socketio`.
    *   Runs on port `3005` (backend) / `3000-3002` (frontend).
    *   **Bot Logic**: `bot_agent.py` contains the decision engine (Reflex + Heuristic).

## 📂 Key Files Map
| Component | File Path | Purpose |
| :--- | :--- | :--- |
| **Frontend** | `frontend/components/AIStudio.tsx` | Main UI for AI features (Tabs, Video, Generator). |
| **API API** | `controllers.py` | endpoints: `/submit_training`, `/analyze_screenshot`, `/ask_strategy`. |
| **AI Client** | `ai_worker/llm_client.py` | `GeminiClient` class handling Google API calls. |
| **Database** | `models.py` | Defines `bot_training_data` table. |
| **Settings** | `settings.py` | Configures Logging, DB, and Upload paths. |
| **Logs** | `logs/debug.log` | **READ THIS FIRST** to debug backend logic. |

## 🛠️ Debugging Guide
### Backend Logging
- We use a file-based logger. **Do not use `print()`**.
- Use `logger.debug("message")` in `controllers.py` or `common.py`.
- View logs via: `type logs\debug.log` (Windows) or `tail -f logs/debug.log`.
- **Warning**: Do NOT use `grep` in the terminal (it fails on Windows). Use the `grep_search` tool or `findstr` / `Select-String`.

### Frontend Debugging
- `console.log` is active in `trainingService.ts`.
- Check Browser Console for API payload errors.

## 🚀 Workflows
- **Start Stack**: `python run_game_server.py` + `npm run dev` (in frontend).
- **Docker Setup**: Run `scripts/ensure_docker.ps1` to auto-launch Docker Desktop.
- **Redis**: Required for "Brain" learning. Run `docker-compose up -d redis`.
- **Offline Mode**: Set `OFFLINE_MODE=true` in env or `settings.py` to disable Redis checks during development.
- **Restart Server**: If you edit `controllers.py` or `models.py`, you **MUST** kill the python process (port 3005) and restart it.
- **Verify AI**: Upload a screenshot in Studio. If it fails, check `logs/debug.log` for Gemini API errors.

## 🔮 Future Context
- **Gemini vs YOLO**: We currently use Gemini (slow, accurate) to gather data. The long-term goal is to train a YOLOv8 model using the `uploads/dataset/` images we are collecting now.
- **Redis**: Redis is currently optional for Studio but required for the "Bot Worker". If Redis fails, Studio still works.

***End of Handover***
