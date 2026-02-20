# Next Session Brief — Multiplayer Phase

> **Updated**: 2026-02-20 (late night) | **Lead**: Claude MAX | **Phase**: Multiplayer (MP)
>
> ### ⚡ Session Note
> All QA tasks (MP1 Docker, MP2 Stats API, Baseline) are **VERIFIED GREEN**.
> Claude Desktop MCP config debugged — corrected Playwright (`@playwright/mcp`),
> SQLite (`uvx mcp-server-sqlite`), removed unsupported Dart MCP.
> Guide saved in Antigravity brain artifacts.
> Next: proceed to **M-MP3** (Flutter Auth Flow).

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

Missing:             Matchmaking queue, ELO rating,
                     session recovery, Flutter auth UI
```

---

## Mission Plan

### Phase A — Identity & Server (Claude + Jules)

| Mission | Owner | Status | Description |
|---------|-------|--------|-------------|
| **M-MP1**: Server Dockerfile | Jules | ✅ Done + QA Verified | Docker build & compose |
| **M-MP2**: Player Stats API | Jules | ✅ Done + QA Verified | 10/10 tests passing |
| **M-MP3**: Auth Flow (Flutter) | Claude | 🔜 Next | Login/signup/guest + JWT persistence |
| **M-MP4**: Session Recovery | Claude | Pending | Reconnect after app restart |

### Phase B — Matchmaking & Ranking (Claude + Jules)

| Mission | Owner | Description | Depends On |
|---------|-------|-------------|------------|
| **M-MP5**: ELO Rating Engine | Jules | ELO calculation, K-factor, placement matches | M-MP2 |
| **M-MP6**: Matchmaking Queue | Claude | Server-side queue with skill matching | M-MP5 |
| **M-MP7**: Quick Match UI | Claude | Queue screen, finding opponent animation | M-MP6 |
| **M-MP8**: Leaderboard UI | Jules | Flutter leaderboard + tier badges | M-MP5 |

### Phase C — Polish & Testing

| Mission | Owner | Description | Depends On |
|---------|-------|-------------|------------|
| **M-MP9**: Integration Tests | Jules | Server multiplayer test suite | M-MP6 |
| **M-MP10**: Load Testing | Antigravity | Concurrent player stress test | M-MP9 |
| **M-MP11**: Security Hardening | Claude | JWT rotation, CORS production, rate limits | M-MP1 |

---

## Agent Assignments — Next Wave

### Claude MAX: M-MP3
- Flutter auth screens (Login/Signup/Guest)
- JWT token persistence + auth state management

### Jules: M-MP5 (after M-MP3)
- ELO rating engine module

### Antigravity: QA standby
- Ready to verify M-MP3 Flutter auth flow

---

## Codebase Stats
- **Python tests**: 550 passing | **Flutter tests**: 151 passing | **TypeScript**: 0 errors
- **Flutter analyze**: 137 info-level issues (non-blocking)
- **11 multiplayer missions planned** across 3 phases
