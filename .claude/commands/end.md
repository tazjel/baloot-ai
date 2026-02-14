End-of-session wrap-up for Baloot AI. Run ALL steps in order:

## 1. Health Check
Run these in parallel:
- `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`
- `cd frontend && npx tsc --noEmit`
- `git status --short`

## 2. Uncommitted Work
If there are ANY uncommitted changes:
- Review what changed (git diff --stat)
- Stage and commit with a clear message describing what was done this session
- Push to remote

If git is clean, skip this step.

## 3. Update Mission Brief
Read `.agent/next-session-brief.md` and update it:
- Mark any missions completed this session as ✅ with a summary of what was built
- Update the test count if it changed
- Update the TypeScript error count
- Make sure the "Active Missions" section reflects current state

## 4. Update Memory
Read your memory file and update it:
- Add any new completed missions to the Completed Missions list
- Update test count if changed
- Add any new patterns, conventions, or lessons learned this session
- Remove or correct any outdated information
- Keep MEMORY.md under 200 lines

## 5. Session Summary
Present a final report:

```
## Session Summary

### What was done
- [Bullet list of accomplishments]

### Final health
| Check | Status |
|-------|--------|
| Tests | X passing |
| TypeScript | X errors |
| Git | clean ✅ / pushed to [commit hash] |

### Next session should
- [What to work on next, based on priority matrix]
- [Any blockers or warnings for next session]
```

## Rules
- Do NOT skip the health check. If tests fail, fix them before ending.
- Do NOT leave uncommitted work. Commit and push everything.
- Do NOT start new work. This command is for wrapping up only.
- Be concise. The summary should fit on one screen.
