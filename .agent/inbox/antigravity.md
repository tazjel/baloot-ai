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

**Locust example** (save as `tests/load/locustfile.py`):
```python
"""Load test for matchmaking queue using Locust + socketio."""
import socketio
from locust import User, task, between

class MatchmakingUser(User):
    wait_time = between(1, 3)

    def on_start(self):
        self.sio = socketio.Client()
        self.sio.connect('https://baloot-server-1076165534376.me-central1.run.app')

    def on_stop(self):
        self.sio.disconnect()

    @task
    def join_queue(self):
        self.sio.emit('queue_join', {'playerName': f'LoadTest-{self.environment.runner.user_count}'})
```

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

### PENDING — QA-Security: Verify M-MP11 Security Hardening
**Priority**: MEDIUM | **Added by**: Claude MAX | **Date**: 2026-02-21

After pulling latest main (`d7c1496`), verify security hardening:

```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai"
git pull origin main

# Run security tests
python -m pytest tests/server/test_security.py -v --tb=short

# Run all server tests
python -m pytest tests/server/ --tb=short -q --ignore=tests/server/test_stress_game.py

# Run Flutter tests
cd mobile
flutter test
```

**Expected**: 25 security tests + 128 total server tests + 174 Flutter tests

**Report format:**
```
### QA-Security: M-MP11 Verification
- Security tests: X/25 passed
- All server tests: X/128 passed
- Flutter tests: X/174 passed
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

### SUPERSEDED — QA-MP3, QA-MP5, QA Jules PRs
- These tasks are no longer needed — Claude MAX built all MP missions directly.
- M-MP3 through M-MP9 all verified and committed to main.

---

## Notes
- Always `git pull origin main` before starting any task
- If a command fails, report the error — don't try to fix code
- Post results in this file AND in `.agent/knowledge/agent_status.md`
- Current main: `254a3be` (after session brief update)
