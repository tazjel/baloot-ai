---
description: Restart the Game Server (Clean + Launch)
---

This workflow performs a clean restart of the Baloot Game environment.
It deliberately closes existing game console windows ("Baloot Backend", "Baloot Frontend") to prevent clutter, then launches the full stack.

1. **Restart Game Stack**
   // turbo
   ```powershell
   powershell -ExecutionPolicy Bypass -File ./scripts/launch/launch_ww.ps1
   ```
