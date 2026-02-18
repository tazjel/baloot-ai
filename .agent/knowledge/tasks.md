# Active Task Distribution — 2026-02-18 (Updated v2)

> **M-F8**: ✅ | **M-F9**: ✅ | **M-F11**: ✅ | **QA 6-8**: ✅ Antigravity done | **QA 10+**: 🔲 Antigravity next

---

## Claude MAX — Building M-F12

### ✅ Completed This Session
- M-F8: Online multiplayer (`294a1fd`)
- M-F9: Game over, persistence, haptics, theme, overlays (`b65d9f3` → `7cd5ba9`)
- M-F11: Profile screen + match history (`55b5e62` → `cecb414`)
- RTL toast fix (from Antigravity QA finding)

### 🔄 Current: M-F12 Release Prep + Polish

---

## Jules — New Tasks Assigned

| Task | Status | Session ID |
|------|--------|------------|
| M-F7 Tests | ✅ Done | `15951593649281280163` |
| Room Code Widget | ✅ Done | `14347506078552313448` |
| **M-F9 Tests** | 🔄 Assigned | _(new session)_ |

**M-F9 Tests spec**: Game over dialog, settings persistence, theme toggle, round transition, progress bar

---

## Antigravity — Next Tasks

> **IMPORTANT**: Tasks 6-8 are DONE (good work!). Now do these:

### Priority 1: Analyze + Test (must do first)
| # | Task | Command |
|---|------|---------|
| 10 | `flutter analyze` | `cd mobile && flutter analyze` |
| 11 | `flutter test` | `cd mobile && flutter test` — expect 130+ pass |

### Priority 2: Visual QA (after analyze passes)

**Pull latest first**: `git pull origin main`

| # | Task | What to check |
|---|------|---------------|
| 19 | Game Over dialog | Play solo vs bots, let match reach 152 GP. Verify full-screen overlay with scores + round history |
| 20 | Round transition overlay | After each round ends, verify brief score summary popup |
| 21 | Match progress bar | Look at top HUD — blue/red bars should grow toward 152 |
| 22 | Lobby stats | After finishing 1+ games, return to lobby — verify games/won/% chips |
| 23 | Theme toggle | Lobby: tap moon/sun icon top-left. Settings dialog: dark mode switch |
| 24 | Settings persistence | Change difficulty to Easy, close app, reopen — should still be Easy |
| 25 | Name persistence | In multiplayer, enter a name, leave, come back — name should be pre-filled |
| 28 | Profile screen | Navigate to /profile from lobby — verify avatar, name, tier badge, stats cards, win rate ring |
| 29 | Match history | After 2+ games, check profile — last 10 matches with win/loss, scores, time ago |
| 30 | Profile empty state | Clear app data, open profile — verify "لم تلعب أي مباراة بعد" message |
| 27 | Final full test run | `flutter test` — all pass |

### Commands
```powershell
git pull origin main
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" analyze
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" test
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" run -d chrome
```

---

## File Locks
None active.
