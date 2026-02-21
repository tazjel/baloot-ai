End-of-session wrap-up for Baloot AI. Run ALL steps in order:

## 1. Health Check
Run in parallel:
- `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q 2>&1 | tail -3`
- `git status --short`

## 2. Uncommitted Work
If there are uncommitted changes:
- `git diff --stat` to review
- Stage, commit with clear message, push to remote
If git is clean, skip this step.

## 3. Update Session Brief
Read `.agent/next-session-brief.md` and update it with:
- What was done this session
- Current state and next steps
- Updated test counts and git hash

## 4. Update Memory
Read your MEMORY.md and update if needed:
- New patterns or lessons learned
- Updated test counts
- Remove outdated info
- Keep under 200 lines

## 5. Session Summary
```
## Session Summary

### What was done
- [Bullet list]

### Final health
| Check | Status |
|-------|--------|
| Tests | X passing |
| Git | pushed to [hash] |

### Next session should
- [Priority items]
```

## Rules
- Do NOT skip the health check.
- Do NOT leave uncommitted work.
- Do NOT start new work.
- Be concise.
