# Next Session Brief — Flutter Mobile Migration

> **Updated**: 2026-02-18 | **Focus**: M-F5 complete → M-F6 (Qayd) → M-F7 (Testing)

## Current Status: M-F5 Animations (Complete)

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

### M-F5 Delivery Summary
**Animation files created (3):**
- `spring_curves.dart` — 6 SpringDescription configs (Framer Motion), 4 CSS cubic-bezier curves, 12 duration constants
- `card_animations.dart` — AnimatedCardDeal, AnimatedCardPlay, AnimatedTrickSweep, AnimatedThump, AnimatedFloorReveal
- `ui_animations.dart` — AnimatedToastEntry, AnimatedSpeechBubble, HintPulseEffect, TrumpShimmerEffect, TurnIndicatorPulse, AnimatedScoreFlash, AnimatedKabootBurst

**Wiring completed (5 files modified):**
- `GameArena` — table cards: AnimatedCardPlay + AnimatedThump; floor card: AnimatedFloorReveal
- `HandFanWidget` — cards: AnimatedCardDeal (staggered) on new deal detection
- `ToastOverlay` — toasts: AnimatedToastEntry (slide-in + auto-hide)
- `PlayerAvatarWidget` — avatar: TurnIndicatorPulse; speech: AnimatedSpeechBubble
- `GameScreen` — added HeartbeatLayer + HintOverlayWidget overlays

**All M-F4 widgets delivered:**
- Claude MAX: 9 core widgets + 2 screens
- Antigravity: 10 modals/screens (match_review, dispute, store, sawa, variant_selection, settings_dialog, replay_controls, level_up, project_selection, multiplayer)
- Jules: 13 simple widgets (suit_icon, score_badge, contract_indicator, turn_timer, glass_panel, game_toast, speech_bubble, hint_overlay, heartbeat_layer, project_reveal, emote_menu, score_sheet, error_boundary)

---

## Next: M-F6 Qayd Dispute System & Edge Cases

### For Claude MAX
| Task | Details |
|------|---------|
| QaydOverlay | Dispute wizard container with 6-state machine |
| QaydCardSelector | Trick browser + card picker for crime/proof |
| Sawa flow | Claim → opponent responses → resolve/penalty |
| Akka declaration | HOKUM-only, leading-only validation |

### For Jules (Module Generation)
| Task | Details |
|------|---------|
| QaydMainMenu | Violation type selection grid |
| QaydVerdictPanel | Result display with penalty summary |
| QaydFooter | Confirm/cancel action buttons |
| Project conflicts | Multi-player project resolution logic |
| Fast-forward mode | Speed up to 150ms bot turns |
| Baloot declaration | K+Q of trump, immune to multipliers |
| Error boundaries | ErrorWidget.builder for graceful degradation |

### Edge Cases Checklist
- [ ] Sawa: claim → 3s timer → opponents can challenge → resolve
- [ ] Akka: only in HOKUM, only when leading, requires K+Q of trump
- [ ] Kawesh: pre-bid worthless hand redeal
- [ ] Waraq/Gash: 3 passes + dealer waraq → redeal with dealer rotation
- [ ] Project conflicts: 4 players declare simultaneously → resolve
- [ ] Doubling: NORMAL → DOUBLE → TRIPLE → QUADRUPLE → GAHWA
- [ ] Qayd 6-step: IDLE → MENU → VIOLATION → CRIME_CARD → PROOF_CARD → VERDICT
- [ ] Fast-forward: toggle button speeds bot actions to 150ms
- [ ] Baloot GP: always 2, immune to all multipliers, added last

---

## MCP & Tooling
- **Dart MCP server** configured in `.mcp.json` with Flutter SDK path
- Provides: error analysis, symbol resolution, package search, testing, formatting
- Available on next Claude Code session restart

---

## Key Architecture Notes

### Type Patterns (Critical for new code)
```dart
// GameMode enum, NOT String
sortHand(cards, GameMode.hokum);

// Suit? for trump, NOT String?
isValidMove(card: c, hand: h, tableCards: tc, mode: m, trumpSuit: s, isLocked: false);

// gameStateProvider returns AppGameState, NOT GameState
final appState = ref.watch(gameStateProvider);
final gameState = appState.gameState; // Access GameState
```

### Provider Hierarchy
```
gameStateProvider (master AppGameState)
  ├── gameSocketProvider (socket → state updates)
  ├── biddingLogicProvider (PASS/SUN/HOKUM/ASHKAL)
  ├── playingLogicProvider (card play + doubling)
  ├── roundManagerProvider (round lifecycle)
  ├── actionDispatcherProvider (facade)
  ├── gameRulesProvider (computed: legalCardIndices, canDouble, isMyTurn)
  ├── audioNotifierProvider
  ├── botSpeechProvider
  ├── toastProvider
  ├── connectionStatusProvider
  ├── emoteProvider
  ├── shopProvider
  ├── tensionProvider
  └── hintProvider
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
| Widgets | 37 | ~6,100 |
| Screens | 3 | ~600 |
| Animations | 3 | ~1,100 |
| Tests | 8 | ~1,500 |
| **Total** | **90** | **~15,600** |

## Git Log (Recent)
```
93545aa feat(M-F5): Wire animations into game widgets
04bd9f7 feat(M-F5): Animation system — spring curves, card animations, UI effects
a5e5d0d feat(M-F4): Jules widgets + warning fixes — 13 new widgets
1450280 feat(M-F4): Phase 2b modals & screens — 10 new widgets
01a283f feat(M-F4): Core widgets & screens — GameScreen Stack, ActionDock, HandFan, HUD
f3f2a69 feat(M-F3): State management — 17 Riverpod notifiers, 102 tests passing
6d1cf8f feat(M-F2): Services layer — SocketService, AccountingEngine
0dc4425 feat(M-F1): Flutter mobile app foundation — models, utils, theme, router
```

## Jules Status
- Session `18051886396563218460` COMPLETED — 13 widgets integrated into main
- No active Jules sessions

## Backend Tests (Unchanged)
- 550 tests passing (`python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`)
- 652 GBaloot tests passing
