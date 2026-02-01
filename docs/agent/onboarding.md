# AGENT_README: Project Knowledge Base

**Welcome, Agent.**
This document serves as your onboarding guide to the Baloot AI Project (React-Py4Web). Use this to orient yourself quickly and work efficiently.

## 🧠 Core Capabilities
The project is a Multiplayer Baloot Game with an advanced "AI Studio" for training bots.

1.  **AI Studio (`/react-py4web`)**:
    *   **Builder Mode**: Manually create or edit game scenarios.
    *   **Training Mode**: Interactive logic puzzles for humans (Lichess-style).
    *   **Bidding Mode**: Batch generator for 5-card bidding scenarios.

## 🔌 Power Skills (Scientific & Creative)
We are a research lab. We value clean code and creative problem-solving. Use these power tools to enhance your workflow, but never let them limit your creativity.

- **React Best Practices**: `.agent/skills/external/skills/react-best-practices`
  *Master the art of modern React integration.*
- **Python Pro**: `.agent/skills/external/skills/python-pro`
  *Advanced Pythonic patterns for scientific computing.*
- **Clean Code**: `.agent/skills/external/skills/clean-code`
  *Keep our lab clean and efficient.*

> **Tip**: See [.agent/skills/SKILLS_INDEX.md](file:///c:/Users/MiEXCITE/Projects/baloot-ai/.agent/skills/SKILLS_INDEX.md) for a complete map of our toolset.

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
| **AI Client** | *Removed* | Gemini integration removed (see `legacy_server_node` for old code). |
| **Database** | `models.py` | Defines `bot_training_data` table. |
| **Settings** | `settings.py` | Configures Logging, DB, and Upload paths. |
| **Logs** | `logs/debug.log` | **READ THIS FIRST** to debug backend logic. |

## 🛠️ Power Tools (New!)
The environment is now equipped with professional dev tools. Use them to work faster:

### 1. JSON Processing (`jq`)
Parse logs and API responses instantly.
```powershell
# Example: Extract all 'BID_PLACED' events from logs
type logs/debug.log | rg "BID_PLACED" | jq .details
```

### 2. Fast Search (`rg`)
Use `ripgrep` instead of slow `findstr` or `grep`.
```powershell
# Example: Find where 'calculate_score' is defined
rg "def calculate_score"
```

### 3. API Testing (`http`)
Use `httpie` for cleaner API requests.
```powershell
# Example: Ping the server
http :3005/
```

### 4. Load Testing (`locust`)
Stress test the game server.
```powershell
# Example: Run load test
locust -f scripts/load_test.py
```

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
- **Gemini (Removed)**: The "Free Gemini" integration has been removed to reduce dependency on external APIs.
- **YOLO Training**: The long-term goal is to train a local YOLOv8 model for card recognition. We need to collect data manually or implement a local perception tool.
- **Redis**: Required for the "Bot Worker" brain.

## 🛡️ Agent Survival Guide (Tips & Tricks)
1.  **Project Location**: ALWAYS ensure you are working in `C:\Users\MiEXCITE\Projects\baloot-ai`. The old `Downloads` path is deprecated.
2.  **Git Hygiene**:
    *   **Large Files**: NEVER commit `.mp4` or heavy datasets. Checks are in place, but be vigilant.
    *   **Pushing**: If `git push` fails, check if the repo exists or if you are authenticated as `tazjel`.
3.  **Tool Quirks**:
    *   **GitHub CLI**: `gh` is installed. Use `gh pr list` or `gh issue view` to manage the repo.
    *   **File Locks**: Windows locks files easily (especially logs/DBs). If a delete fails, the server might still be running.
4.  **Verification**:
    *   Always run `npm run dev` and `python run_game_server.py` to verify the "full stack" after major changes.

***End of Handover***
