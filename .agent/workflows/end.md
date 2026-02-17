---
description: Safely end the session by syncing with remote and committing changes (handles concurrent work).
---

# End Session (Safe Sync)

Safely wrap up work, handling potential concurrent changes from other agents (e.g., Claude).

1. **Check Remote Status**
   // turbo
   ```powershell
   git remote update
   git status -uno
   ```

2. **Finalize Documentation**
   // turbo
   Update `task.md`, `walkthrough.md`, and generate `next-session-brief.md`.
   ```powershell
   # Manual step: Ensure artifacts are up to date
   ```

3. **Stage and Commit (Local Savepoint)**
   - Review changes first.
   // turbo
   ```powershell
   git add .
   git commit -m "wip: end of session savepoint [Antigravity/Gemini]"
   ```
   - *Note: If you have a specific message, amend this commit.*

3. **Pull Latest Changes (Rebase)**
   // turbo
   ```powershell
   git pull --rebase
   ```
   - If conflicts occur, resolve them manually or ask the user.

4. **Push to Remote**
   // turbo
   ```powershell
   git push
   ```

5. **Final Status Check**
   // turbo
   ```powershell
   git status
   ```
