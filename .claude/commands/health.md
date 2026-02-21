Run the full health check pipeline for the Baloot AI project:

Run these in parallel:
1. `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q 2>&1 | tail -5`
2. `git status --short`

Report results in a table:

```
| Check | Status |
|-------|--------|
| Python Tests | X passing |
| Git | clean / N uncommitted |
```

If any check fails, diagnose the issue and suggest a fix. Do NOT fix anything automatically — just report.
