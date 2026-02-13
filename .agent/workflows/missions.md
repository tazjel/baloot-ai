---
description: Scan the codebase and generate improvement missions with actionable tasks
---

// turbo-all

# Generate Improvement Missions

## 1. Scan Backend Hotspots
Use the `find_by_name` tool to list all `.py` files in `game_engine/`, `ai_worker/`, and `server/`. The results include file sizes. Note files >15 KB as complexity hotspots. Do NOT use shell commands for file sizes — `find_by_name` already returns them.

## 2. Scan Frontend Hotspots
Use the `find_by_name` tool to list all `.tsx` and `.ts` files in `frontend/src/`. Note files >10 KB as complexity hotspots. Do NOT use shell commands for file sizes — `find_by_name` already returns them.

## 3. Check TypeScript Health
Use the `grep_search` tool to search for `as any` in `frontend/src/` (includes: `*.tsx`, `*.ts`). Count the results. Zero is healthy.

## 4. Check Test Health
**File coverage ratio:** Use `find_by_name` to list all `.py` files in `tests/`. Compare against backend source count from step 1. Ratio >0.7 is healthy.

**Dashboard health data:** Use `view_file` on `tools/dashboard/test_history.json` (if it exists) to read the last test run entry. Extract:
- `passed` / `total` → Last Pass Rate %
- `coverage` → Last Code Coverage % (if present)
- `timestamp` → When tests were last run

Include all three metrics in the Health Dashboard table.

## 5. Check for Code Smells
Use `grep_search` for each of these patterns:
- `as any` in `frontend/src/` (includes: `*.tsx`, `*.ts`)
- `console.log` in `frontend/src/` (includes: `*.tsx`, `*.ts`) — exclude `devLogger.ts`
- `TODO|FIXME|HACK` (regex) in `game_engine/`, `ai_worker/`, `server/`, `frontend/src/`

## 6. Read Current Mission State
Use `view_file` on `.agent/next-session-brief.md` to see completed and active missions.

## 7. Generate Missions Document
Based on ALL the data collected from steps 1-6, overwrite `.agent/next-session-brief.md` with updated missions.

The document must start with a **Health Dashboard** table summarizing all scan metrics, then list **Completed Missions** (marked ✅), then **Active Missions**.

Each active mission should follow this template:

```markdown
## Mission N: "Code Name" — One-Line Description
> Effort estimate (~X hours)

### Tasks
- [ ] **Task Name** — specific, actionable description
  - [ ] Sub-task with exact file references

### Key Files
| File | Change |
|------|--------|

### Verification
- Exact commands or steps to verify the mission is complete
```

**Mission Priorities** — order by:
1. Low-risk hygiene
2. Structural refactoring (files >15KB)
3. Test coverage gaps
4. User-facing features (UX, animations, sounds)
5. Bot AI intelligence
6. Multiplayer/production features

## 8. Commit and Push
Commit the updated `.agent/next-session-brief.md` and push to origin. Use PowerShell-compatible command chaining (`;` not `&&`):
// turbo
```
git add .agent/next-session-brief.md; git commit -m "docs: regenerate improvement missions"; git push origin main
```
