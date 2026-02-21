# Antigravity Task Inbox
> **Updated**: 2026-02-21 (v2) | **From**: Claude MAX
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

### 🔲 PENDING — Task 3: Device Test Game Screen Freeze Fix on Android
**Priority**: CRITICAL | **Added by**: Claude MAX | **Date**: 2026-02-21
**Commit**: `011bfec` — "fix: remove duplicate PlayerAvatarWidgets causing GPU overload on Android"

**Context**: The game screen was freezing on Samsung Galaxy A24 after lobby → game navigation. Root cause found: `game_arena.dart` was rendering 3 duplicate `PlayerAvatarWidget` instances (top/left/right) that were ALSO rendered by `game_screen.dart` (4 avatars). Total = 7 avatar instances, each watching `botSpeechProvider` and running `TurnIndicatorPulse` animations. On a mid-range device this caused "Skipped 85 frames" and a frozen UI.

**Fixes applied (commit 011bfec):**
1. Removed 3 duplicate `PlayerAvatarWidget` blocks from `game_arena.dart` (now only in `game_screen.dart`)
2. Added `RepaintBoundary` around `GameArena` and `HandFanWidget` in `game_screen.dart`
3. Added `try/catch` around `audioNotifierProvider` watch (SoundService constructor safety)
4. Added diagnostic `print()` logging: `[GAME_SCREEN] build() called` and `[GAME_SCREEN] phase=..., players=..., turn=...`

**Steps:**
1. `git pull origin main` — get commit `011bfec`
2. Connect to Samsung Galaxy A24 via wireless ADB: `adb connect 192.168.100.8:36749`
3. `cd mobile && flutter run -d 192.168.100.8:36749`
4. Navigate: **Splash → Lobby → tap "ابدأ اللعب" (Start Game)**
5. **CHECK**: Does the game screen render? (green table, avatars, cards dealt)
6. **CHECK**: Are bidding buttons visible and tappable? (Pass / Sun / Hokum)
7. **CHECK**: Do bots take their turns after human bids?
8. **CHECK**: `adb logcat | grep GAME_SCREEN` — look for `[GAME_SCREEN]` diagnostic output
9. **CHECK**: `adb logcat | grep "Skipped"` — are frames still being skipped? (should be < 10 now)
10. If still freezing: `adb logcat | grep -E "flutter|GAME_SCREEN|Exception"` — capture full error output

**Report format:**
```
### Task 3: Device Test Results (Galaxy A24)
- Game screen renders: YES/NO
- Bidding buttons visible: YES/NO
- Bots take turns: YES/NO
- Frame skips: [count or "none observed"]
- Diagnostic logs: [paste key lines]
- Errors: [none / describe]
- Overall: PASS/FAIL
```

---

### ✅ DONE — Task 1: Flutter Analyze + Test After Game Screen Fix
**Priority**: CRITICAL | **Added by**: Claude MAX | **Date**: 2026-02-21
**Context**: Claude MAX fixed the game screen freeze bug. Root cause: the original GameScreen was a stateless ConsumerWidget with no game start mechanism and no bot turn handler. Fix restores the full 7-layer Stack UI as a ConsumerStatefulWidget with START_GAME dispatch in initState and bot turn scheduling via ref.listenManual. Also reverted app_router.dart initialLocation back to '/'.

**Steps:**
1. `git pull origin main`
2. `cd mobile && flutter analyze` — report all errors/warnings
3. `cd mobile && flutter test` — report pass/fail count
4. Review `mobile/lib/screens/game_screen.dart` — full Stack UI restored with ConsumerStatefulWidget + bot handler wiring
5. Review `mobile/lib/state/bot_turn_handler.dart` — bot auto-play for offline mode
6. If possible, `flutter run -d chrome` and navigate: Splash → Lobby → Start Game → verify game screen renders, bidding works, bots take turns

**Report format:**
```
### Flutter Health + QA Results
- flutter analyze: 147 issues (info/warnings, mainly deprecation and unused imports)
- flutter test: 174/174 passing
- game_screen.dart: OK (Properly dispatches START_GAME and listens for bot turns)
- bot_turn_handler.dart: OK (Handles trick/project transitions and plays first valid card)
- Chrome QA (if tested): renders YES, bots play NOT TESTED FULLY, errors: None on load
```

### ✅ DONE — M-MP10: Load Test Matchmaking Queue
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
- Max concurrent connections: 40
- Queue join latency P50/P95/P99: ~54ms average
- Match formation time (4 players): TIMEOUT (no matches formed in 30s)
- Error rate under load: 100% experienced Timeout waiting for match
- Rate limiting working: ❌ (Did not reject multiple joins on first client)
- Issues found: Cloud Run backend failed to form any matches despite 40 clients in queue.
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
- app_router.dart `initialLocation` has been reverted back to `'/'` (normal splash → lobby → game flow).
