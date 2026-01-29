---
description: Initialize the agent session efficiently. Reads only essential context (Claims Windows/Tips) and prepares a plan without deep-diving into full documentation.
---

# Start Session (Lean Boot)

This workflow "boots up" the agent's context using the **"High Value, Low Token"** strategy.

1.  **Environment Constraints (Read Carefully)**:
    - **OS**: Windows (Paths use `\`, but `/` works in code).
    - **Shell**: PowerShell (Do NOT use `export` or `&&`).
    - **Redis**: Must be running. Check with `Get-Process redis-server -ErrorAction SilentlyContinue`.

2.  **Load "The Brain" (Essential Context)**:
    - **Read** `.gemini/antigravity/brain/$UUID/task.md` (or generic `task.md` path).
        - *Goal*: Identify the active task and next steps.
    - **Read** `CODEBASE_MAP.md` (if likely relevant).
        - *Goal*: Understand the file structure without expensive directory listings.

3.  **Load "Safety Rails"**:
    - **Read** `.agent/knowledge/developer_tips.md` OR `development/troubleshooting.md`.
        - *Goal*: Avoid known pitfalls (e.g., "Restart server after patching FastGame").

4.  **Verification**:
    - **Do NOT** read the "Comprehensive Project Handbook" or `current_state.md`.
    - **Do NOT** list large directories (`node_modules`, `venv`).

5.  **Action Plan**:
    - Based *only* on the above:
        1.  List **Ideas** for this session.
        2.  List **Concrete Tasks**.
    - Ask the user: "Ready to execute?"
