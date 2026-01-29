---
description: "End Session: Update Tasks & Git Push (Low Token Usage)"
---

This workflow is designed to quickly wrap up the session with minimal context reading (saving tokens) while ensuring work is saved.

1. **Quick Doc Update**
   - Check `task.md` and ensure all completed items are marked `[x]`.
   - if `task.md` is clean, skip to the next step.
   - Do NOT perform deep file analysis or creating new summaries unless necessary.

2. **Git Commit & Push**
   - Stage all changes.
   - Commit with a message derived from the last completed task in `task.md`.
   - Push to current branch.
   
   // turbo
   ```powershell
   git add .
   git commit -m "feat: Progress update (Automated Session End)" 
   git push origin main
   ```
   *(Note: The agent should replace the commit message with something specific if possible, e.g., "feat: Implemented Commissioner's Desk")*

3. **Farewell**
   - Notify the user that the session is verified, saved, and synced.
