# Active Task Distribution — 2026-02-18 (Updated v4)

> **M-F1→17**: ✅ All Done | **M-F18**: 🔄 Jules | **M-F19**: 🔄 Claude | **QA+Tests**: 🔲 Antigravity

---

## Claude MAX — Current: M-F19 E2E Polish

### ✅ Completed (All Sessions)
- M-F1→M-F14: Full Flutter app (99 lib files, 17 test files)
- M-F15: Custom app icon (gold spade on dark background) — `8ce5c27`
- M-F16: Build config (ProGuard, minify, portrait lock) — `1c9bd9d`
- M-F17: Offline font bundling (Tajawal Arabic, google_fonts removed) — `4aaad8d`

### 🔄 Current: M-F19 E2E Polish
- Fix any bugs found by Antigravity QA
- Final cleanup before store submission

---

## Jules — Sessions

| Task | Status | Session ID |
|------|--------|------------|
| M-F7 Tests | ✅ Done | `15951593649281280163` |
| Room Code Widget | ✅ Done | `14347506078552313448` |
| M-F12 Tests (4 files) | ✅ Done | `767214469817076241` |
| M-F17: Offline Font | ✅ Done (no branch pushed, Claude did it) | `15723797855726962685` |
| **M-F18: A11y Tests** | 🔄 Running | `3685688760499618959` |

### ⚠️ Known Jules Issues
Jules consistently fails to deliver usable output:
1. **Never pushes branches** or creates PRs despite `autoCreatePR: true`
2. **Deletes/modifies files** outside its scope (confetti, accessibility, etc.)
3. **Session completes** but no artifacts are available to cherry-pick

### 🔧 Antigravity Task: Fix Jules Configuration
**Please investigate and fix the Jules GitHub App setup so it actually works.**

Steps:
1. Go to https://jules.google.com and check the app installation status
2. Verify the `tazjel/baloot-ai` repo has proper permissions (read + write)
3. Check if Jules needs a specific branch protection or webhook config
4. Try creating a small test session to verify Jules can push branches:
   ```
   Prompt: "Create a file mobile/test/jules_test_probe.dart with a single test that prints 'Jules works'"
   Repo: tazjel/baloot-ai
   Branch: main
   autoCreatePR: true
   ```
5. If Jules pushes a branch → the setup works, delete the probe file
6. If Jules fails → document what's wrong in this file under "Jules Status"

**Goal**: Next time Claude delegates to Jules, the output should be cherry-pickable.

---

## Antigravity — Tasks

> **Pull latest first**: `git pull origin main`

### 🔴 Priority 1: Run Tests + Analyze (BLOCKING)
These MUST be done first. Report results to Claude.

| # | Task | Command | Expected |
|---|------|---------|----------|
| 10 | `flutter analyze` | `cd mobile && flutter analyze` | 0 errors |
| 11 | `flutter test` | `cd mobile && flutter test` | 100+ pass |
| 39 | Report results | Post output in status board below | — |

### 🟡 Priority 2: Jules Configuration Fix
See "🔧 Antigravity Task: Fix Jules Configuration" section above.

### 🟢 Priority 3: Visual QA — Game Features
Run the app with `flutter run -d chrome` and check each feature:

| # | Task | What to check |
|---|------|---------------|
| 19 | Game Over dialog | Play vs bots to 152 GP. Full-screen overlay with scores + round history + confetti on win |
| 20 | Round transition | After round ends, brief score summary popup appears |
| 21 | Match progress bar | Top HUD — blue/red bars growing toward 152 |
| 22 | Lobby stats | After 1+ games, return to lobby — games/won/% chips + streak fire |

### 🟢 Priority 4: Visual QA — Polish Features

| # | Task | What to check |
|---|------|---------------|
| 23 | Theme toggle | Lobby moon/sun icon top-left, settings dialog dark mode switch |
| 24 | Settings persistence | Change difficulty to Easy, reopen — still Easy |
| 25 | Name persistence | Enter name in multiplayer, leave and return — pre-filled |
| 28 | Profile screen | Navigate /profile — avatar, name, tier badge, stats, win rate ring |
| 29 | Match history | After 2+ games, profile shows last 10 matches |
| 30 | Profile empty state | Clear data → "لم تلعب أي مباراة بعد" |

### 🟢 Priority 5: Visual QA — Recent Features (M-F12→M-F17)

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
| 40 | App icon | Check app icon is gold spade on dark background (not default Flutter icon) |
| 41 | Font rendering | Arabic text renders in Tajawal font (not system default) |
| 42 | Portrait lock | Rotate device — app stays portrait |

### Commands
```powershell
git pull origin main
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" analyze
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" test
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" run -d chrome
```

---

## Antigravity Results (Post here)

### flutter analyze
```
(paste output here)
```

### flutter test
```
(paste output here)
```

### Visual QA Findings
| # | Task | Result | Notes |
|---|------|--------|-------|
| 19 | | ⬜ | |
| 20 | | ⬜ | |
| ... | | | |

### Jules Configuration
```
(paste findings here)
```

---

## File Locks
None active.
