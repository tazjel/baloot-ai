# Antigravity Task Inbox
> **Updated**: 2026-02-21 | **From**: Claude MAX
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

### 🔴 PENDING — Task 1: Flutter Health Check (Game Screen Freeze Debug)
**Priority**: CRITICAL | **Added by**: Claude MAX | **Date**: 2026-02-21
**Context**: The game screen freezes/crashes when navigating from lobby. We've stripped the GameScreen to a minimal diagnostic UI to isolate the issue.

**Steps:**
1. `git pull origin main`
2. `cd mobile && flutter analyze` — report all errors/warnings
3. `cd mobile && flutter test` — report pass/fail count
4. Check `mobile/lib/screens/game_screen.dart` — it's currently a minimal diagnostic UI (just text + buttons, no complex widgets). Confirm the build method looks sane.
5. Check `mobile/lib/state/bot_turn_handler.dart` — new file, verify no obvious issues
6. Check `mobile/lib/state/action_dispatcher.dart` — verify print() logging is in place

**Report format:**
```
### Flutter Health Check Results
- flutter analyze: X issues (list errors if any)
- flutter test: X/Y passing
- game_screen.dart: OK/ISSUE (describe)
- bot_turn_handler.dart: OK/ISSUE (describe)
- action_dispatcher.dart: OK/ISSUE (describe)
```

### 🔴 PENDING — Task 2: Chrome QA of Diagnostic Game Screen
**Priority**: HIGH | **Added by**: Claude MAX | **Date**: 2026-02-21
**Context**: GameScreen is stripped to diagnostic UI. Test on Chrome web to check console output.

**Steps:**
1. `cd mobile && flutter run -d chrome`
2. Open Chrome DevTools Console (F12)
3. App should go directly to game screen (initialLocation is '/game')
4. Look for these print messages in console:
   - `[GAME] GameScreen.initState called`
   - `[GAME] PostFrame: phase=...`
   - `[GAME] Dispatching START_GAME`
   - `[GAME] START_GAME done, phase=...`
   - `[GAME] PostFrame2: phase=..., turn=..., isBot=...`
   - `[BOT] phase=..., turn=...`
   - `[BOT] executing turn for player...`
   - `[DISPATCHER] Player Action: ...`
5. Report: Does the game screen render? Does bidding happen? Do bots play?
6. Screenshot the Chrome page and console output

**Report format:**
```
### Chrome QA Results
- Game screen renders: YES/NO
- Console prints visible: YES/NO (list key messages seen)
- Bidding phase works: YES/NO
- Bots take turns: YES/NO
- Any errors in console: (list)
- Screenshot: (attach or describe)
```

### 🔴 PENDING — M-MP10: Load Test Matchmaking Queue
**Priority**: HIGH | **Added by**: Claude MAX | **Date**: 2026-02-21
**Depends on**: GCP Cloud Run deployment (✅ done by Antigravity)

The matchmaking queue (M-MP6) is built and the backend is deployed to Cloud Run.
Now we need to stress test it under concurrent load.

**Backend URL**: `https://baloot-server-1076165534376.me-central1.run.app`

**What to test:**
1. **Concurrent WebSocket connections** — Simulate 20-50 players connecting simultaneously
2. **Queue join/leave throughput** — Players joining and leaving the `queue_join` / `queue_leave` events
3. **Match formation latency** — How fast does the server form a 4-player match?
4. **Reconnection under stress** — Disconnect/reconnect during queue
5. **Rate limiting** — Verify server rejects >5 queue joins/min per SID

**Socket.IO Events to test:**
```
# Join queue
emit('queue_join', {playerName: 'TestPlayer1'})
# → callback: {success: true, queueSize: N, avgWait: N}

# Leave queue
emit('queue_leave', {})
# → callback: {success: true}

# Match found (server → client)
on('match_found', {roomId: '...', yourIndex: 0-3})

# Queue status
emit('queue_status', {})
# → callback: {queueSize: N, avgWait: N}
```

**Suggested tools**: `locust` (Python, already installed), `k6`, or `artillery`

**Report format:**
```
### M-MP10: Load Test Results
- Max concurrent connections: X
- Queue join latency P50/P95/P99: Xms/Xms/Xms
- Match formation time (4 players): Xms
- Error rate under load: X%
- Rate limiting working: ✅/❌
- Issues found: (list any)
```

---


## Completed Tasks

### DONE — QA-MP1: Docker Build (2026-02-20)
- Build: OK | Server start: OK | Errors: None

### DONE — QA-MP2: Stats API (2026-02-20)
- pytest: 10 passed | Errors: None

### DONE — QA-Baseline (2026-02-20)
- Python: 550 passing | Flutter: 151 passing | Analyze: 137 info-level

### DONE — GCP Deployment + Fastlane (2026-02-21)
- Backend deployed to Cloud Run: `23320c6`
- Fastlane authenticated for Google Play Console
- Session handoff doc: `f018416`

### DONE — QA-Security: M-MP11 Verification (2026-02-21)
- Security tests: 25/25 passed
- All server tests: 128/128 passed
- Flutter tests: 174/174 passed
- Issues found: None. Security hardening fully verified.

### SUPERSEDED — QA-MP3, QA-MP5, QA Jules PRs
- These tasks are no longer needed — Claude MAX built all MP missions directly.
- M-MP3 through M-MP9 all verified and committed to main.

---

## Notes
- Always `git pull origin main` before starting any task
- If a command fails, report the error — don't try to fix code
- Post results in this file AND in `.agent/knowledge/agent_status.md`
- **IMPORTANT**: app_router.dart `initialLocation` is currently set to `/game` (skip splash/login/lobby) for debugging. This is intentional.
