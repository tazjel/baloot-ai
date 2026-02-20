# Antigravity Task Inbox
> **Updated**: 2026-02-20 (night) | **From**: Claude MAX
> **Protocol**: Read this file at the START of every session. Execute all PENDING tasks. Mark DONE when finished. Push results.

## How This Works
1. Claude MAX pushes tasks here after completing work
2. Antigravity reads this file on session start
3. Execute tasks marked PENDING in order
4. Update status to DONE with results
5. Push changes: `git add .agent/ && git commit -m "QA: [summary]" && git push`
6. If blocked, mark BLOCKED with reason

---

## Active Tasks

### PENDING — QA-MP3: Flutter Auth Flow Verification
**Priority**: HIGH | **Added by**: Claude MAX | **Date**: 2026-02-20

M-MP3 auth code is written but NOT tested. Verify compilation and existing tests.

```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
flutter analyze
flutter test
```

**What to check:**
- Does `flutter analyze` pass with 0 errors? (warnings/info OK)
- Do all existing 151 tests still pass?
- Any compilation errors in the new auth files?

New files to verify:
- `lib/services/auth_service.dart`
- `lib/state/auth_notifier.dart`
- `lib/screens/login_screen.dart`
- `lib/screens/signup_screen.dart`
- `lib/screens/splash_screen.dart`

**Report format**:
```
### QA-MP3: Flutter Auth
- flutter analyze: X errors
- flutter test: X/151 passing
- New file compilation: OK/FAIL
- Issues found: (list any)
```

---

### PENDING — QA-MP5: ELO Engine Tests
**Priority**: HIGH | **Added by**: Claude MAX | **Date**: 2026-02-20

Once M-MP5 code is pulled to main, verify ELO engine tests:

```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai"
python -m pytest tests/server/test_elo_engine.py --tb=short -q
python -m pytest tests/server/ --tb=short -q
```

**Report format**:
```
### QA-MP5: ELO Engine
- ELO tests: X passed
- All server tests: X passed
- Issues found: (list any)
```

---

### PENDING — QA-Baseline: Full Regression Check
**Priority**: MEDIUM | **Added by**: Claude MAX | **Date**: 2026-02-20

```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai"
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q

cd mobile
flutter test

cd ../frontend
npx tsc --noEmit
```

**Expected**: 550 Python + 151 Flutter + 0 TS errors
**Report format**:
```
### Baseline Regression
- Python bot+game_logic: X/550
- Flutter: X/151
- TypeScript: X errors
```

---

### PENDING — QA Jules PRs: M-MP8 + M-MP9 (when they arrive)
**Priority**: MEDIUM | **Added by**: Claude MAX | **Date**: 2026-02-20

Jules is being dispatched on M-MP8 (Leaderboard UI) and M-MP9 (Integration Tests).
When PRs appear on GitHub, checkout and verify:

**For M-MP8:**
```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
flutter analyze
flutter test
```

**For M-MP9:**
```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai"
python -m pytest tests/server/ --tb=short -q
```

---

### FUTURE — M-MP10: Load Testing (after M-MP6 matchmaking is done)
**Priority**: LOW (not ready yet) | **Added by**: Claude MAX | **Date**: 2026-02-20

When matchmaking queue (M-MP6) is deployed:
- Simulate 50 concurrent WebSocket connections
- Measure matchmaking queue response times under load
- Test reconnection handling under stress
- Report latency P50/P95/P99
- Tool suggestion: use `locust` or `k6` for load testing

---

## Completed Tasks

### DONE — QA-MP1: Docker Build (2026-02-20)
- Build: OK | Server start: OK | Errors: None

### DONE — QA-MP2: Stats API (2026-02-20)
- pytest: 10 passed | Errors: None

### DONE — QA-Baseline (2026-02-20)
- Python: 550 passing | Flutter: 151 passing | Analyze: 137 info-level

---

## Notes
- Always `git pull origin main` before starting any task
- If a command fails, report the error — don't try to fix code
- Post results in this file AND in `.agent/knowledge/agent_status.md`
