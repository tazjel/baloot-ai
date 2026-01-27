---
description: Update all documentation and record session lessons/tips for the next agent session (Alias for /finalize-session).
---

# Finalize Session & Knowledge Transfer

This workflow ensures the codebase is clean, documentation is up-to-date, tests pass, and critical context is preserved.

1.  **Verify System Health (Smoke Test)**:
    - Ensure recent changes didn't break core game logic.
    // turbo
    python -m pytest tests/test_game_logic.py

2.  **Clean Up & Logs**:
    - Truncate the main server log to save space for the next session.
    // turbo
    Write-Output "" > logs/server_manual.log

3.  **Update "Brain" Artifacts**:
    - **task.md**: Mark all completed items as `[x]`. Ensure the "Next Steps" section is populated.
    - **walkthrough.md**: Add a final "Verification Results" section summarizing the last stable state (e.g., "Server running, New Game fixed").

4.  **Update Persistent Knowledge**:
    - **.agent/knowledge/developer_tips.md**: Add any specific "Gotchas" found today (e.g., "Restart server after patching FastGame").
    - **.agent/knowledge/project_status.md** (if exists): Update the "Current Phase" or "Recent Achievements".
    - **CODEBASE_MAP.md**: Update if any new directories were created (e.g., `ai_worker/professor.py`).

5.  **Context for Next Agent**:
    - Create a "Handover Note" in `task.md` or a new file if needed, explaining exactly where we left off (e.g., "Professor is debuggable, but UI needs polish").

6.  **Final Polish**:
    - **README.md**: If high-level features changed (e.g., "Added War Room"), update the features list.
