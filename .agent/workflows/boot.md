---
description: Initialize the agent session efficiently with Git sync check and conflict prevention.
---

# Start Session (Lean Boot v2)

This workflow "boots up" the agent's context using the **"High Value, Low Token"** strategy, with added **Git Sync** to prevent conflicts from Claude Desktop or other tools.

## 1. Environment Constraints (Read Carefully)

- **OS**: Windows (Paths use `\`, but `/` works in code).
- **Shell**: PowerShell (Do NOT use `export` or `&&`).
// turbo
- **Redis**: Check with `Get-Process redis-server -ErrorAction SilentlyContinue`.

## 2. Git Sync Check (Conflict Prevention)

// turbo
- Run `git status --short` and `git log -3 --oneline`.
- **If uncommitted changes exist**:
  - Summarize them briefly (files changed, new files).
  - Ask: "Commit now to create a checkpoint?" or "Proceed with caution?"
- **If clean**: Continue silently.
- *Goal*: Prevent conflicts from Claude Desktop, other agents, or manual edits.

## 3. Load "The Brain" (Essential Context)

- **Read** `.agent/knowledge/developer_tips.md`.
  - *Goal*: Avoid known pitfalls (e.g., "Restart server after patching FastGame").
- **Read** `.agent/knowledge/handoff.md` (if exists).
  - *Goal*: Get context from Claude Desktop or previous Antigravity session.
  - If recent (< 24 hours): Summarize key points to user.
- **Read** `task.md` (if exists in `<appDataDir>/brain/<conversation-id>/`).
  - *Goal*: Identify the active task and next steps from prior session.
- **Read** `CODEBASE_MAP.md` (only if task involves navigating unfamiliar code).
  - *Goal*: Understand the file structure without expensive directory listings.

## 4. Last Session Context (Optional)

- If user mentions "I was working in Claude Desktop" or similar:
  - Prioritize `git diff` review.
  - Ask if they want a summary of changes before proceeding.
- If recent conversation summaries are available:
  - Check if any relate to current work.
  - Mention: "I see you were working on [X] recently. Continue?"

## 5. Verification (What NOT to Do)

- **Do NOT** read the "Comprehensive Project Handbook" or `current_state.md` (too large).
- **Do NOT** list large directories (`node_modules`, `venv`, `__pycache__`).
- **Do NOT** run `/check-health` automatically (save tokens; user can request it).

## 6. Action Plan

Based *only* on the above:

1. **Summarize** uncommitted changes (if any).
2. List **Ideas** for this session (based on tips/status).
3. List **Concrete Tasks** (actionable next steps).
4. Ask: "Ready to execute?" or offer specific options.

---

## Quick Reference

| Shortcut | Purpose |
|----------|---------|
| `/check-health` | Verify Redis, Backend, Frontend are running. |
| `/start` | Start the full game stack. |
| `/major-test` | Run 4-bot simulation for stability verification. |
| `/finalize-session` | Update docs and record lessons before ending. |
