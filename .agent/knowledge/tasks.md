# Active Task Distribution — 2026-02-18 (Updated v3)

> **M-F1→14**: ✅ All Done | **M-F15**: 🔄 Claude | **M-F17**: 🔄 Jules | **M-F18**: 🔄 Jules | **QA**: 🔲 Antigravity

---

## Claude MAX — Building M-F15 + M-F16

### ✅ Completed (All Sessions)
- M-F1→M-F12: Full Flutter app (99 lib files, 17 test files)
- M-F13: Accessibility (Semantics on all interactive/live widgets, confetti overlay)
- M-F14: App store naming (Android/iOS/pubspec standardized to بلوت AI)
- Jules test cherry-picks (welcome_dialog, about, persistence, room_code)

### 🔄 Current: M-F15 App Icons + M-F16 Build Config

---

## Jules — Active Sessions

| Task | Status | Session ID |
|------|--------|------------|
| M-F7 Tests | ✅ Done | `15951593649281280163` |
| Room Code Widget | ✅ Done | `14347506078552313448` |
| M-F12 Tests (4 files) | ✅ Done | `767214469817076241` (cherry-picked) |
| **M-F17: Offline Font** | 🔄 Running | `15723797855726962685` |
| **M-F18: A11y Tests** | 🔄 Running | `3685688760499618959` |

⚠️ **Jules cherry-pick rule**: Jules modifies/deletes files it shouldn't. ALWAYS:
1. `git fetch --all`
2. `git diff --stat main..origin/jules-<id>-<hash>` to see what changed
3. `git checkout origin/jules-<branch> -- <specific files>` only for new test/font files
4. NEVER merge the full branch

---

## Antigravity — QA Tasks (M-F9 → M-F14)

> **Pull latest first**: `git pull origin main`
> Then run analyze + test, then visual QA

### Priority 1: Analyze + Test
| # | Task | Command |
|---|------|---------|
| 10 | `flutter analyze` | `cd mobile && flutter analyze` |
| 11 | `flutter test` | `cd mobile && flutter test` — expect 130+ pass |

### Priority 2: Visual QA — Game Features
| # | Task | What to check |
|---|------|---------------|
| 19 | Game Over dialog | Play vs bots to 152 GP. Full-screen overlay with scores + round history + confetti on win |
| 20 | Round transition | After round ends, brief score summary popup appears |
| 21 | Match progress bar | Top HUD — blue/red bars growing toward 152 |
| 22 | Lobby stats | After 1+ games, return to lobby — games/won/% chips + streak fire |

### Priority 3: Visual QA — Polish Features
| # | Task | What to check |
|---|------|---------------|
| 23 | Theme toggle | Lobby moon/sun icon top-left, settings dialog dark mode switch |
| 24 | Settings persistence | Change difficulty to Easy, reopen — still Easy |
| 25 | Name persistence | Enter name in multiplayer, leave and return — pre-filled |
| 28 | Profile screen | Navigate /profile — avatar, name, tier badge, stats, win rate ring |
| 29 | Match history | After 2+ games, profile shows last 10 matches |
| 30 | Profile empty state | Clear data → "لم تلعب أي مباراة بعد" |

### Priority 4: Visual QA — New Features (M-F12→M-F14)
| # | Task | What to check |
|---|------|---------------|
| 31 | Splash screen | App launch → gold shimmer animation → auto-navigate to lobby |
| 32 | Welcome dialog | First launch → 3-page tutorial, page dots, next/previous buttons |
| 33 | About screen | Lobby → "حول التطبيق" → all sections, footer "صُنع بـ ❤️ في السعودية" |
| 34 | Tips of the day | Lobby → rotating tip card between multiplayer and about buttons |
| 35 | Win streak | Win 2+ games → fire icon in lobby stats + streak in profile |
| 36 | Accessibility | Enable TalkBack/VoiceOver → cards announce rank+suit, buttons have labels |
| 37 | App name | Settings → About phone → App name shows "بلوت AI" (not baloot_ai) |
| 38 | Confetti | Win a match → gold confetti particles fall over game over dialog |
| 39 | Final full test | `flutter analyze && flutter test` — all clean |

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
