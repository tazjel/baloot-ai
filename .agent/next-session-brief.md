# Next Session Brief — Flutter Mobile Migration

> **Updated**: 2026-02-18 | **Lead**: Claude MAX | **Support**: Jules (modules), Antigravity (tests/analyze)

---

## Master Plan — Remaining Missions

### ✅ COMPLETED
| Phase | Commit | Owner |
|-------|--------|-------|
| M-F1: Foundation & Core Models | `0dc4425` | Claude |
| M-F2: Services Layer | `6d1cf8f` | Claude |
| M-F3: State Management | `f3f2a69` | Claude |
| M-F4: All Widgets (3 phases) | `a5e5d0d` | Claude + Jules + Antigravity |
| M-F5: Animations (system + wiring) | `93545aa` | Claude |
| M-F6: Qayd Core (6-step wizard) | `d9502ca` | Claude |
| M-F6: Edge Cases (Akka, Kawesh, Baloot, FF) | `de60048` | Claude |
| M-F7: Integration Tests | `b9d497f` | Jules + Antigravity |
| M-F8: Online Multiplayer | `294a1fd` | Claude |
| M-F9: Game Over + Persistence + Polish | `b65d9f3`→`7cd5ba9` | Claude |
| M-F9: Haptics + Name Persistence | `60ff198` | Claude |
| M-F10: Theme Persistence + Dark Mode | `8512d9e` | Claude |
| M-F11: Profile Screen + Match History | `55b5e62`→`cecb414` | Claude |
| M-F12: Release Prep + Polish | `bea0fd8`→`4863013` | Claude |
| M-F12: Tests (4 files) | `35e06fd` | Jules (cherry-picked) |
| M-F13: Accessibility | `d4d5b6d`→`06942db` | Claude |
| M-F13: Victory Confetti | `3d80ceb` | Claude |
| M-F14: App Store Naming | `08b8bf2` | Claude |

### 🔄 IN PROGRESS
| Task | Owner | Status |
|------|-------|--------|
| Visual QA (tasks 10-30) | **Antigravity** | Assigned |

### 📋 UPCOMING
| Mission | Description | Owner | Priority |
|---------|-------------|-------|----------|
| **M-F15: App Icons** | Custom app icon artwork (replace Flutter defaults) | Designer/Claude | 🟡 Medium |
| **M-F16: Build Config** | ProGuard, signing, release mode optimization | Claude | 🟢 Low |
| **M-F17: Offline Font Bundling** | Bundle Tajawal .ttf for offline Arabic support | Claude | 🟢 Low |

---

## What's Been Built (This Session — Continuation)

### M-F13: Accessibility (`d4d5b6d` → `06942db`)
- **Card Semantics**: Arabic rank/suit labels (سبعة سبيت, إكة هاص, etc.) + state info (محددة, حكم, يمكن لعبها)
- **Player Semantics**: Name, bot status, turn indicator, dealer badge
- **HUD Semantics**: Score summary label (النتيجة: نحن X - هم Y)
- **Action dock Semantics**: All 3 button types (_BidButton, _SmallButton, _ActionButton), bidding/doubling/waiting docks
- **Toast Semantics**: liveRegion for screen reader announcements
- **Round transition Semantics**: liveRegion with full round result summary
- **Game over Semantics**: liveRegion with final scores and result text
- **Victory confetti** (`confetti_overlay.dart`): 50-particle CustomPainter animation on win, layered via Stack

### M-F14: App Store Naming (`08b8bf2`)
- **Android**: label `baloot_ai` → `بلوت AI`
- **iOS**: CFBundleDisplayName `Baloot Ai` → `بلوت AI`, CFBundleName → `Baloot AI`
- **pubspec**: Arabic store description

### M-F12: Tests — Jules (`35e06fd`)
- Cherry-picked 4 test files from Jules session `767214469817076241`
- `welcome_dialog_test`: 3-page tutorial navigation, dots, buttons
- `about_screen_test`: all headers, sections, footer
- `settings_persistence_test`: stats, streaks, name, first launch, reset
- `room_code_card_test`: display, copy toggle, Arabic labels

---

## Jules Notes
- Jules consistently completes tasks but **fails to create PRs** even with `autoCreatePR: true`
- Jules pushes branches but no PR — must manually cherry-pick test files
- Jules also modifies/deletes files it shouldn't — **always cherry-pick individual files, never merge**
- Branch naming pattern: `jules-<sessionId>-<hash>`

## Active Delegations

### Antigravity — Visual QA Tasks
- Tasks 10-30: QA for all M-F9 through M-F14 features
- Run `flutter analyze` and `flutter test` after each batch

---

## Team Workflow Rules

| Role | Responsibilities |
|------|-----------------|
| **Claude MAX** | Architecture, complex features, multi-file refactors, strategy design, Jules task delegation |
| **Jules** | Parallel module generation, test file creation, simple self-contained tasks |
| **Antigravity** | Flutter analyze, test execution, UI polish, visual QA, RTL verification |

### Delegation Protocol
- Claude writes features → commits → pushes
- Claude delegates tests to Jules (via `jules new` or MCP)
- Antigravity runs all analyze/test cycles
- Claude never runs `flutter analyze` or `flutter test` — always delegates

---

## Git Log (Recent)
```
35e06fd test(M-F12): Jules tests — welcome dialog, about, persistence, room code
08b8bf2 feat(M-F14): App store naming — standardize to بلوت AI
06942db feat(M-F13): Accessibility — Semantics for action dock, toasts, overlays
3d80ceb feat(M-F13): Victory confetti overlay on game win
d4d5b6d feat(M-F13): Accessibility — semantic labels for cards, players, HUD
ea0b196 docs: update session brief with M-F12 completion
4863013 feat(M-F12): Gameplay tips, haptic feedback on profile
e30298c feat(M-F12): Win streak tracking in lobby and profile
2974f92 feat(M-F12): Page transitions, welcome dialog, first-launch tutorial
d303ac5 docs: update session brief, tasks, agent status for M-F12
d639c7c style: dart fix --apply lint cleanup
bea0fd8 feat(M-F12): Splash screen, about screen, sound persistence, profile polish
```

## Commands
```powershell
# Jules CLI (installed globally)
jules remote list --repo
jules new --repo tazjel/baloot-ai "task description"
jules remote pull --session <ID>

# Flutter (Antigravity runs these)
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" analyze
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" test

# Backend (unchanged — 550 passing)
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q
```
