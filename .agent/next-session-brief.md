# Next Session Brief — Multiplayer Phase

> **Updated**: 2026-02-20 | **Lead**: Claude MAX | **Phase**: Multiplayer (MP)

---

## Previous Phase — ✅ Flutter Mobile: ALL 20 MISSIONS COMPLETE
All Flutter missions (M-F1→M-F20) are done. App is store-ready.
- **Python tests**: 550 passing | **Flutter tests**: 151 passing | **TypeScript**: 0 errors
- Store assets ready in `mobile/store/`
- Manual: needs Google Play account ($25) + keystore for release build

---

## Current Phase — Multiplayer Production (MP)

### Goal
Transform Baloot AI from "friends with room codes" → **public multiplayer with accounts, matchmaking, and ranking**.

### Architecture
```
Backend (existing):  server/routes/auth.py (signup/signin/JWT)
                     server/socket_handler.py (Socket.IO rooms)
                     server/room_manager.py (Redis game state)
                     server/models.py (app_user, game_result, match_archive)

Missing:             Matchmaking queue, player stats API, ELO rating,
                     Dockerfile, session recovery, Flutter auth UI
```

---

## Mission Plan

### Phase A — Identity & Server (Claude + Jules)

| Mission | Owner | Description | Depends On |
|---------|-------|-------------|------------|
| **M-MP1**: Server Dockerfile + deploy config | Jules | Dockerfile for Python server, docker-compose update, env config | — |
| **M-MP2**: Player Stats API | Jules | REST endpoints: GET /stats/:email, GET /leaderboard, POST /game-result | — |
| **M-MP3**: Auth Flow (Flutter) | Claude | Login/signup/guest screens, JWT token persistence, auth state management | M-MP2 |
| **M-MP4**: Session Recovery | Claude | Reconnect to ongoing game after app restart, pending action queue | M-MP3 |

### Phase B — Matchmaking & Ranking (Claude + Jules)

| Mission | Owner | Description | Depends On |
|---------|-------|-------------|------------|
| **M-MP5**: ELO Rating Engine | Jules | Python module: ELO calculation, K-factor, placement matches | M-MP2 |
| **M-MP6**: Matchmaking Queue | Claude | Server-side queue with skill matching, timeout→bot fill, Redis pub/sub | M-MP5 |
| **M-MP7**: Quick Match UI (Flutter) | Claude | Queue screen, finding opponent animation, cancel, estimated wait | M-MP6 |
| **M-MP8**: Leaderboard + Ranking UI | Jules | Flutter screens: leaderboard list, player rank card, tier badges | M-MP5 |

### Phase C — Polish & Testing (Claude + Antigravity)

| Mission | Owner | Description | Depends On |
|---------|-------|-------------|------------|
| **M-MP9**: Integration Tests | Jules | Server multiplayer test suite: room lifecycle, reconnect, matchmaking | M-MP6 |
| **M-MP10**: Load Testing | Antigravity | Concurrent player stress test, network failure simulation | M-MP9 |
| **M-MP11**: Security Hardening | Claude | JWT secret rotation, CORS production config, rate limit tuning | M-MP1 |

---

## Agent Assignments — Current Wave (Phase A)

### Jules: M-MP1 + M-MP2 (parallel)
- **M-MP1**: Dockerfile + docker-compose for server
- **M-MP2**: Player stats REST endpoints

### Antigravity: QA standby
- Verify M-MP1 Docker builds and runs
- Test M-MP2 endpoints with curl

### Claude MAX: M-MP3 (after Jules delivers M-MP2)
- Flutter auth screens + JWT persistence

---

## Codebase Stats
- **~100 lib/ files**, **20 test files**, **~18,500+ lines of Dart**
- **Python tests**: 550 passing | **Flutter tests**: 151 passing | **TypeScript**: 0 errors
- **11 multiplayer missions planned** across 3 phases
