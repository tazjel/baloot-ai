---
description: Serve the Full Game Stack (Redis, AI Worker, Backend, Frontend)
---

This workflow executes the master launch script which handles Docker checks, Redis container management (idempotent), and spawns separate windows for the Backend and Frontend.

1. **Launch Full Stack**
   // turbo
   ```powershell
   powershell -ExecutionPolicy Bypass -File ./scripts/launch/launch_ww.ps1
   ```
