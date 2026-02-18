# Agent Status Board
> Shared status between Antigravity (Gemini), Claude MAX, and Jules.
> Each agent updates their section when completing tasks or requesting work.

## Last Updated: 2026-02-18T23:46+03:00

---

## Antigravity (Gemini) — Status: ✅ ALL TASKS COMPLETE

### Latest: M-F19 Verification ✅
- `flutter analyze` → **0 errors** (137 info-level only)
- `flutter test` → **138/138 pass**
- M-F19 changes (timer fixes, error handler, font cleanup) verified clean

### Store Assets Created ✅
- `mobile/store/listing_ar.md` — Arabic title, descriptions, keywords
- `mobile/store/privacy_policy.md` — Local-only data privacy policy
- `mobile/store/release_signing.md` — Android keystore + iOS signing guide

**Awaiting**: Next task assignment from Claude or user.

---

## Claude MAX — Status: ✅ M-F20 In Progress

### Completed This Session
- **M-F17**: Offline font bundling (Tajawal TTFs, removed google_fonts) — `4aaad8d`
- **M-F19 Round 1**: Memory leak fix, ErrorBoundary init, font cleanup — `d7af95f`
- **M-F19 Round 2**: Timer leaks, null safety, mounted checks — `7801a50`
- **M-F20**: Internet permission, release signing config, .gitignore — `e84615d`

### Jules Sessions (with PR instructions this time!)
- Widget tests: `10744328001566808027` — IN_PROGRESS
- Store assets: `9102467196684113667` — IN_PROGRESS

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
