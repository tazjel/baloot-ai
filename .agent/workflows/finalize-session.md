---
description: Update all documentation and record session lessons/tips for the next agent session (Alias for /finalize-session).
---

# Finalize Session

Wrap up the current session cleanly. Commit everything, leave a clear handoff.

1. **Commit Outstanding Changes**
   // turbo
   ```powershell
   git add -A && git status --short
   ```
   - If there are staged changes, commit with a descriptive message.
   - Push to remote.

2. **Update Handoff Note**
   - Write/update `docs/agent/HANDOFF.md` with:
     - **Session Date** and **Commits** (hash + one-liner)
     - **What Was Done** (2-3 bullet points max)
     - **What's Still Open** (specific next steps, not vague)
     - **Known Gotchas** (anything the next agent should watch out for)

3. **Update CODEBASE_MAP.md** (only if new dirs/files were created)
   // turbo
   ```powershell
   git diff --name-status HEAD~5 HEAD | Select-String "^A"
   ```
   - If new directories were added, update `CODEBASE_MAP.md` with their purpose.

4. **Push Final**
   ```powershell
   git add -A && git commit -m "docs: session handoff" && git push
   ```
