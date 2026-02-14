---
description: Serve the Full Game Stack (Redis, AI Worker, Backend, Frontend)
---

# /WW — Full Stack Launch

// turbo-all

Launches Docker Desktop (if needed), Redis, Backend, and Frontend in one command.

## What It Does

The `launch_ww.ps1` script performs these steps automatically:

| Step | Action | Details |
|------|--------|---------|
| 0 | **Docker Desktop** | Launches Docker Desktop if not running; waits for daemon ready |
| 1 | **Cleanup** | Kills previous Backend/Frontend windows, frees ports 3005 & 5173 |
| 2 | **Redis** | Uses local Redis if available, otherwise starts/creates Docker container |
| 3 | **Backend** | Starts `python -m server.main` (port 3005) |
| 4 | **Frontend** | Starts `npm run dev` in `frontend/` (port 5173) |

## Launch

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/launch/launch_ww.ps1
```

## Options

| Flag | Effect |
|------|--------|
| `-Headless` | No windows; logs to `logs/server_headless.*.log`. Includes auto health-check. |

## After Launch

- **Backend**: http://localhost:3005/health
- **Frontend**: http://localhost:5173
- **Logs**: Check the 2 PowerShell windows, or `logs/server_debug.log`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port 3005/5173 in use | Script auto-kills; if not, run `scripts/launch/cleanup.ps1` |
| Docker timeout | Open Docker Desktop manually, wait for it to fully load |
| Redis connection errors | Check `docker ps` or start local Redis |
