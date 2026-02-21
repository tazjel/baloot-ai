Session kickstart for Baloot AI. Run these steps in order:

## 1. Context Load
Read these files (in parallel):
- `.agent/next-session-brief.md`
- `.agent/knowledge/agent_status.md`

## 2. Quick Health (parallel)
Run ALL of these simultaneously:
- `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q 2>&1 | tail -3`
- `git status --short`
- `git log --oneline -5`

## 3. Report
Present a concise dashboard:

```
## Boot Report — [date]

| Check | Status |
|-------|--------|
| Python Tests | X passing |
| Git | clean / N uncommitted |

### Recent Commits
[list from git log]

### Mission Status
[from next-session-brief.md]

### Agent Status
[from agent_status.md — one line per agent]
```

## 4. Alerts
Flag if:
- Tests are failing
- Uncommitted changes exist
- Agent tasks are stale (>48h)

## Rules
- Do NOT start any work. Just report and wait.
- Do NOT fix anything. Report only.
- Be concise — dashboard should fit on one screen.
- Ask: "What would you like to work on?"
