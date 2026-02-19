# Antigravity Task Inbox
> **Protocol**: Read this file at the START of every session. Execute all PENDING tasks. Mark DONE when finished. Push results.

## How This Works
1. Claude MAX pushes tasks here after completing work
2. Antigravity reads this file on session start
3. Execute tasks marked 🔴 PENDING in order
4. Update status to ✅ DONE with results
5. Push changes: `git add .agent/inbox/antigravity.md && git commit -m "QA: [summary]" && git push`
6. If blocked, mark ⚠️ BLOCKED with reason

---

## Active Tasks

### 🔴 PENDING — QA-MP1: Docker Build Verification
**Priority**: High | **Added by**: Claude MAX | **Date**: 2026-02-20

```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai"
git pull origin main
docker build -t baloot-server .
docker compose up -d
sleep 10
docker compose logs server
docker compose down
```

**Report format**:
- Build: ✅
- Server start: ✅
- Errors: None

---

### 🔴 PENDING — QA-MP2: Stats API Test Run
**Priority**: High | **Added by**: Claude MAX | **Date**: 2026-02-20

```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai"
python -m pytest tests/server/test_stats_api.py --tb=short -q
```

**Expected**: 10 passed
**Report format**:
- Result: 10 passed / 0 failed ✅
- Errors: None

---

### 🔴 PENDING — QA-Baseline: Regression Check
**Priority**: Medium | **Added by**: Claude MAX | **Date**: 2026-02-20

```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai"
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q
cd mobile && flutter test && flutter analyze
```

**Expected**: 550 Python + 151 Flutter passing, 0 analyze errors
**Report format**:
- Python tests: 550 passing ✅
- Flutter tests: 151 passing ✅
- Flutter analyze: 137 issues (Info level, non-blocking as per handoff) ⚠️

---

## Completed Tasks

_(Antigravity: move completed tasks here with results)_

---

## Notes
- Always `git pull origin main` before starting any task
- If a command fails, report the error — don't try to fix code
- Post results in this file AND in `.agent/knowledge/agent_status.md`
- When all PENDING tasks are done, your session is complete
