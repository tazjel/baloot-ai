---
description: Serve the Full Game Stack (Redis, AI Worker, Backend, Frontend)
---

This workflow launches the complete game environment including the new AI subsystem.

1. **Check Docker Status**
   Ensures Docker Desktop is running.
   // turbo
   ```powershell
   pwsh ./scripts/ensure_docker.ps1
   ```

2. **Launch Redis (Infrastructure)**
   // turbo
   ```powershell
   docker run --name baloot-redis -p 6379:6379 -d redis
   ```



4. **Launch Game Server (SocketIO)**
   Run this from `.`
   // turbo
   ```powershell
   python -m server.main
   ```

5. **Launch Frontend (Vite)**
   Run this from `frontend`
   // turbo
   ```powershell
   npm run dev
   ```
