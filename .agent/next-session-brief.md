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

### 🔄 IN PROGRESS
| Task | Owner | Status |
|------|-------|--------|
| M-F7: Integration Tests (4 test files) | **Jules** `15951593649281280163` | Writing tests |
| Flutter analyze + fix warnings | **Antigravity** | Delegated |
| Flutter test baseline verification | **Antigravity** | Delegated |

### 📋 UPCOMING — Claude MAX picks next
| Mission | Description | Owner | Priority |
|---------|-------------|-------|----------|
| **M-F8: Online Multiplayer** | WebSocket integration, room join/create, state sync | Claude | 🔴 High |
| **M-F9: Polish & UX** | Animations tuning, haptics, sound polish, RTL fixes | Claude + Antigravity | 🟡 Medium |
| **M-F10: Settings & Persistence** | SharedPreferences, game settings persistence, theme | Claude | 🟡 Medium |
| **M-F11: Leaderboard & Profile** | User profile screen, match history, league display | Jules (modules) | 🟢 Low |
| **M-F12: Release Prep** | App icons, splash, store listing, build config | Antigravity | 🟢 Low |

---

## Active Delegations

### Jules — Session `15951593649281280163`
**Task**: M-F7 Integration Tests
**Files being created**:
- `mobile/test/utils/akka_utils_test.dart` — 17 tests (Akka, Kawesh, Baloot, scanHand)
- `mobile/test/state/baloot_detection_test.dart` — 5 tests (provider transitions)
- `mobile/test/state/bidding_kawesh_test.dart` — 3 tests (KAWESH action)
- `mobile/test/state/fast_forward_test.dart` — 3 tests (toggle)
**When done**: Antigravity pulls PR, runs `flutter test`, fixes any failures

### Antigravity — Ongoing
**Tasks**:
1. `flutter analyze` on commit `de60048` — fix any warnings
2. `flutter test` — verify 102 baseline still passes
3. When Jules PR arrives → review, merge, run full test suite
4. Report final test count back

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
de60048 feat(M-F6): Edge cases — Akka, Kawesh, Baloot detection, fast-forward
d9502ca feat(M-F6): Qayd dispute system — 6-step wizard + ActionDock edge cases
93545aa feat(M-F5): Wire animations into game widgets
04bd9f7 feat(M-F5): Animation system — spring curves, card animations, UI effects
```

## Commands
```powershell
# Jules CLI (installed globally)
jules remote list --repo              # List repos
jules new --repo tazjel/baloot-ai "task description"  # New task
jules remote pull --session <ID>      # Pull results

# Flutter (Antigravity runs these)
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" analyze
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" test

# Backend (unchanged — 550 passing)
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q
```
