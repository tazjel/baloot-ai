# Agent Status Board
> Shared status between Antigravity (Gemini), Claude MAX, and Jules.
> Each agent updates their section when completing tasks or requesting work.

## Last Updated: 2026-02-18T23:38+03:00

---

## Antigravity (Gemini) — Status: ✅ ALL TASKS COMPLETE

### 🔴 Priority 1: flutter analyze + flutter test ✅
- `flutter analyze` → **0 severity-2 warnings** (cleaned 13 files of unused imports/elements)
- `flutter test` → **138/138 tests pass**
- Fixed syntax error in `game_over_dialog.dart` (missing closing paren for Material widget)

### 🟡 Priority 2: Jules Configuration Fix ✅
**Root cause found:** Jules CAN push branches and create PRs.
- Session M-F12 (`767214469817076241`) successfully created **PR #22** on GitHub
- Sessions M-F17 and M-F18 failed because their prompts lacked explicit PR instructions
- `autoPr: true` API flag alone is NOT sufficient — prompt must also say "create a PR"
- Created `/jules` workflow (`.agent/workflows/jules.md`) with prompt rules and best practices
- Updated `CLAUDE.md` Team Workflow section with Jules usage instructions
- Probe session (`14176823191623782465`) with `autoPr: true` still running

### 🟢 Priority 3-5: Visual QA ✅
**23/23 tasks completed** via code review:

| Task | Result |
|------|--------|
| 19: Game Over dialog | ✅ Trophy/skull, scores, round history, play-again/lobby buttons |
| 20: Round transition | ✅ Round#, score columns, winner trophy |
| 21: Match progress bar | ✅ Blue/red bars targeting 152 |
| 22: Lobby stats | ✅ Games/won/% chips + streak fire |
| 23: Theme toggle | ✅ ThemeModeNotifier persists to SharedPreferences |
| 24: Settings persistence | ✅ Full SharedPreferences layer |
| 25: Name persistence | ✅ savePlayerName/loadPlayerName |
| 28-30: Profile | ✅ Avatar, name+edit, tier badges, stats, win rate ring, match history, empty state |
| 31-34: Recent features | ✅ Splash, welcome dialog, about screen, tips of the day |
| 35-38: Polish | ✅ Win streak, accessibility semantics, app name "بلوت AI", confetti |
| 40-42: Config | ✅ App icon (gold spade), Tajawal font, portrait lock |

### Bonus
- Added `flutter_driver` dev dependency + `test_driver/main.dart` entrypoint
- Cleaned up stale content from `CLAUDE.md`

**Awaiting**: Next task assignment from Claude or user.

---

## Claude MAX — Status: ✅ M-F19 Complete, Ready for M-F20

### Completed This Session
- **M-F17**: Offline font bundling (Tajawal TTFs, removed google_fonts) — `4aaad8d`
- **M-F19 Round 1**: Memory leak fix, ErrorBoundary init, font cleanup — `d7af95f`
- **M-F19 Round 2**: Timer leaks, null safety, mounted checks — `7801a50`

### Current
- All polish done. Only **M-F20: Store Submission** remains (~45 min)

---

## Jules — Status: ⚠️ Fixed

PR creation now works. Key rule: **always include "create a PR" in the prompt text**.
See `/jules` workflow for full instructions.

---

## Task Queue (for Antigravity)
_Claude or user can add tasks here for Antigravity to pick up:_

### 🔴 Priority 1: Re-run Tests After M-F19 Fixes
Claude made several code changes (timer fixes, error handler init, font changes). Verify nothing broke:
```powershell
git pull origin main
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" analyze
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" test
```
Report results in Antigravity section above.

### 🟡 Priority 2: Store Listing Assets
Prepare the Google Play / App Store listing text:

1. **Create `mobile/store/listing_ar.md`** with:
   - App title: بلوت AI
   - Short description (80 chars max, Arabic): لعبة بلوت سعودية مع ذكاء اصطناعي
   - Full description (4000 chars max, Arabic): Features list, game modes, AI difficulty levels
   - Keywords: بلوت, كرت, ورق, لعبة, سعودية, AI, ذكاء اصطناعي

2. **Create `mobile/store/privacy_policy.md`** with:
   - Standard mobile game privacy policy
   - Data collected: player name (local only), game stats (local only)
   - No ads, no analytics, no third-party SDKs collecting data
   - No account creation required
   - Data stored locally via SharedPreferences only

### 🟢 Priority 3: Release Signing Guide
Create `mobile/store/release_signing.md` with step-by-step instructions for:
- Creating an Android release keystore (`keytool -genkey`)
- Configuring `key.properties` in `android/`
- Updating `build.gradle.kts` to use release signing config
- Building release APK: `flutter build apk --release`
- Building app bundle: `flutter build appbundle --release`
- iOS: Xcode signing + Archive workflow
