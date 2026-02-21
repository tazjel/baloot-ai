End-of-session wrap-up for Baloot AI. Run ALL steps in order:

## 1. Git Status
- `git status --short` — check for uncommitted work

## 2. Uncommitted Work
If there are uncommitted changes:
- `git diff --stat` to review
- Stage, commit with clear message, push to remote
If git is clean, skip this step.

## 3. Update Session Brief
Read `.agent/next-session-brief.md` and update it with:
- What was done this session
- Current state and next steps
- Updated git hash

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

### Final state
| Check | Status |
|-------|--------|
| Git | pushed to [hash] |

### Next session should
- [Priority items]
```

## Rules
- Do NOT leave uncommitted work.
- Do NOT start new work.
- Be concise.
