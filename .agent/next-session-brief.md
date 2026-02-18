# Next Session Brief — Flutter Mobile Migration

> **Updated**: 2026-02-18 | **Focus**: M-F6 in progress → finish edge cases → M-F7 (Testing)

## Current Status: M-F6 Qayd Dispute System (In Progress)

### Completed Phases
| Phase | Status | Commit | Tests |
|-------|--------|--------|-------|
| M-F1: Foundation & Core Models | ✅ Complete | `0dc4425` | 30 |
| M-F2: Services Layer | ✅ Complete | `6d1cf8f` | 40 |
| M-F3: State Management | ✅ Complete | `f3f2a69` | 102 |
| M-F4 Phase 1: Core Widgets (Claude) | ✅ Complete | `01a283f` | 102 |
| M-F4 Phase 2b: Modals & Screens (Antigravity) | ✅ Complete | `1450280` | 102 |
| M-F4 Phase 2a: Simple Widgets (Jules) | ✅ Complete | `a5e5d0d` | 102 |
| M-F5: Animation System | ✅ Complete | `04bd9f7` | 102 |
| M-F5: Animation Wiring | ✅ Complete | `93545aa` | 102 |
| M-F6: Qayd Core (6-step wizard) | ✅ Complete | `d9502ca` | 102 |

### M-F6 Delivery So Far
**New files created (5 dispute sub-widgets):**
- `dispute/qayd_types.dart` — Enums (MainMenuOption, ViolationType), CardSelection, VerdictData, constants
- `dispute/qayd_main_menu.dart` — 3-button menu (كشف الأوراق, سوا خاطئ, أكة خاطئة) + waiting state
- `dispute/qayd_card_selector.dart` — Trick browser with crime (pink) / proof (green) card selection
- `dispute/qayd_verdict_panel.dart` — Verdict banner, evidence cards, penalty display
- `dispute/qayd_footer.dart` — Timer circle, reporter badge, back button

**Rewritten:**
- `dispute_modal.dart` — Full 6-step orchestrator (227→360 lines), timer management, auto-confirm

**Modified:**
- `action_dock.dart` — Added Qayd trigger (⚖) + Sawa claim (🤝) buttons to PlayingDock
- `game_screen.dart` — Wired DisputeModal + SawaModal as Positioned.fill overlay layers

---

## Remaining M-F6 Work (Next Session)

### Edge Cases Still Needed
| Task | Status | Details |
|------|--------|---------|
| Akka button in ActionDock | Pending | HOKUM-only, leading-only, uses canDeclareAkka() |
| Kawesh button in BiddingDock | Pending | Pre-bid, uses canDeclareKawesh() |
| Fast-forward toggle | Pending | Speed up bot turns to 150ms |
| Baloot declaration UI | Pending | K+Q of trump auto-detect toast |
| Waraq/redeal handling | Pending | 3 passes + dealer waraq → state reset |
| Jules widgets review | Pending | Session `14611954312806542087` — check if delivered |

### Edge Cases Checklist
- [x] Qayd 6-step: IDLE → MENU → VIOLATION → CRIME_CARD → PROOF_CARD → VERDICT
- [x] Sawa button in PlayingDock
- [x] Qayd trigger button in PlayingDock
- [x] DisputeModal + SawaModal wired into GameScreen Stack
- [ ] Akka: only in HOKUM, only when leading
- [ ] Kawesh: pre-bid worthless hand redeal
- [ ] Fast-forward: toggle button speeds bot actions to 150ms
- [ ] Baloot GP: auto-detect K+Q of trump, toast notification

---

## Key Architecture Notes

### Type Patterns (Critical for new code)
```dart
// gameStateProvider returns AppGameState, NOT GameState
final appState = ref.watch(gameStateProvider);
final gameState = appState.gameState;

// Qayd actions via socket:
ref.read(gameSocketProvider.notifier).sendAction('QAYD_TRIGGER');
ref.read(actionDispatcherProvider.notifier).handlePlayerAction('SAWA_CLAIM');
```

### Dispute Sub-Widget Imports
```dart
import 'dispute/qayd_types.dart';       // Enums, CardSelection, VerdictData
import 'dispute/qayd_main_menu.dart';   // QaydMainMenu
import 'dispute/qayd_card_selector.dart'; // QaydCardSelector
import 'dispute/qayd_verdict_panel.dart'; // QaydVerdictPanel
import 'dispute/qayd_footer.dart';      // QaydFooter
```

---

## Test Command
```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" test
```

## File Counts
| Category | Files | Lines |
|----------|-------|-------|
| Models | 10 | ~1,200 |
| Utils | 7 | ~800 |
| Services | 5 | ~1,500 |
| State (Notifiers) | 17 | ~2,800 |
| Widgets | 42 | ~7,600 |
| Screens | 3 | ~650 |
| Animations | 3 | ~1,100 |
| Tests | 8 | ~1,500 |
| **Total** | **95** | **~17,150** |

## Git Log (Recent)
```
d9502ca feat(M-F6): Qayd dispute system — 6-step wizard + ActionDock edge cases
93545aa feat(M-F5): Wire animations into game widgets
04bd9f7 feat(M-F5): Animation system — spring curves, card animations, UI effects
a5e5d0d feat(M-F4): Jules widgets + warning fixes — 13 new widgets
```

## Jules Status
- Session `14611954312806542087` — M-F6 Qayd Sub-Widgets (delegated, check status)
- Previous: `18051886396563218460` COMPLETED — 13 widgets integrated

## Backend Tests (Unchanged)
- 550 tests passing (`python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`)
- 652 GBaloot tests passing
