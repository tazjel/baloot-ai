Run the full health check pipeline for the Baloot AI project:

1. Run Python tests: `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`
2. Run TypeScript type check: `cd frontend && npx tsc --noEmit`
3. Check for uncommitted changes: `git status`
4. Report results in a table format with pass/fail status

If any check fails, diagnose the issue and suggest a fix. Do NOT fix anything automatically — just report.
