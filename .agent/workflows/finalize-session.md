---
description: Update all documentation and record session lessons/tips for the next agent session.
---

# Finalize Session & Knowledge Transfer

This workflow ensures the codebase is clean, documentation is up-to-date, and critical context is preserved for the next session.

1. **Analyze Codebase Changes**:
   - Review recent file moves (e.g., `scripts/verification`, `ai_worker/data`).
   - Identify any new dependencies or import path changes.

2. **Update Structural Documentation**:
   - **CODEBASE_MAP.md**: Update to reflect the current directory structure (remove `backend/`, add `ai_worker/data`, etc.).
   - **task.md**: Ensure all completed items are checked off.

3. **Record Developer Tips & Tricks (Context Transfer)**:
   - Create or Update `.agent/knowledge/developer_tips.md` (or add a new Knowledge Item) with:
     - **Critical Import Paths**: e.g., `from ai_worker.agent import BotAgent`.
     - **Command Shortcuts**: e.g., "Use `python scripts/verification/verify_*.py` for tests".
     - **Gotchas**: Any errors encountered today and how to avoid them (e.g. `backend/` folder is gone).
     - **Next Session To-Dos**: Explicit instructions for the next agent.

4. **Update Feature Documentation**:
   - Review `docs/` for outdated references to moved files.
   - Update `README.md` if high-level workflows changed.

5. **Self-Correction Check**:
   - Did we leave the codebase in a compilable state?
   - Are there any broken symlinks or references?
