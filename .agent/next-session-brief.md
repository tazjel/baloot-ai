# Next Session Brief — Flutter Mobile Migration

> **Updated**: 2026-02-18 | **Focus**: M-F4 → M-F5 → M-F6 → M-F7

## Current Status: M-F4 Core Widgets (In Progress)

### Completed Phases
| Phase | Status | Commit | Tests |
|-------|--------|--------|-------|
| M-F1: Foundation & Core Models | ✅ Complete | `0dc4425` | 30 |
| M-F2: Services Layer | ✅ Complete | `6d1cf8f` | 40 |
| M-F3: State Management | ✅ Complete | `f3f2a69` | 102 |
| M-F4: Core Widgets (Phase 1) | ✅ Complete | `01a283f` | 102 |

### M-F4 Phase 1 Delivery (Done)
Built 11 widget/screen files (+2,673 lines), all 102 tests passing:

**Claude MAX built (9 new widgets):**
- `CardWidget` — Card face/back with selection, trump glow, hint highlight
- `PlayerAvatarWidget` — Avatar, turn halo, timer ring, dealer badge, speech bubble
- `GameArena` — Center play area, felt gradient, floor card, cross-formation table cards
- `HandFanWidget` — Card fan at bottom, tap-select, double-tap-play, legal move filtering
- `ActionDock` — 4-mode dock: bidding/playing/doubling/waiting + AnimatedSwitcher
- `TableHudWidget` — Score pills, contract badge, doubling level
- `VictoryModal` — Win/lose with scores, rematch/home
- `RoundResultsModal` — Scoring breakdown table
- `ConnectionBanner` — Disconnected/reconnecting bar

**Rewritten screens (2):**
- `GameScreen` — Full 7-layer Stack architecture
- `LobbyScreen` — Settings card with difficulty, timer, strict mode

---

## M-F4 Phase 2: Remaining Widgets (Delegate to Jules + Gemini)

### For Jules (Simple Widgets — ~15 files)
| Widget | Port From | Estimated Lines |
|--------|-----------|-----------------|
| `SuitIconWidget` | Suit display | 50 |
| `ScoreBadgeWidget` | Animated score counter | 80 |
| `ContractIndicator` | Standalone contract badge | 60 |
| `TurnTimerWidget` | Circular countdown | 100 |
| `GlassPanelWidget` | Backdrop blur container | 50 |
| `GameToastWidget` | Toast notification display | 80 |
| `SpeechBubbleWidget` | Bot speech fade anim | 70 |
| `HintOverlayWidget` | AI hint card highlight | 100 |
| `HeartbeatLayer` | Tension pulse overlay | 80 |
| `ProjectRevealWidget` | Project declaration display | 100 |
| `EmoteMenuWidget` | Emoji grid dock | 120 |
| `ScoreSheetWidget` | Round-by-round score table | 150 |
| `ErrorBoundary` | ErrorWidget.builder wrapper | 40 |

### For Gemini/Antigravity (Modals & Screens — ~8 files)
| Widget/Screen | Port From | Estimated Lines |
|---------------|-----------|-----------------|
| `MultiplayerScreen` | Room create/join, player list | 250 |
| `MatchReviewModal` | Trick-by-trick replay | 300 |
| `DisputeModal` (Qayd) | Multi-step wizard | 350 |
| `StoreModal` | Card backs + table skins grid | 200 |
| `LevelUpModal` | Level up notification | 100 |
| `ProjectSelectionModal` | Project picker | 120 |
| `SawaModal` | Sawa claim/response | 150 |
| `VariantSelectionModal` | R2 suit picker | 120 |

---

## M-F5: Animations (Next for Claude MAX)

### Priority Animations
| Animation | Approach | Priority |
|-----------|----------|----------|
| Card deal stagger | Staggered `SlideTransition` from deck to hand | P1 |
| Card play trajectory | `CurvedAnimation` bezier path hand→table | P1 |
| Trick sweep | `SlideTransition` 4 cards → winner corner | P1 |
| Hand fan hover lift | `AnimatedContainer` y-offset on selection | P2 |
| Trump reveal 3D flip | `Transform.rotateY` + glow | P2 |
| Turn indicator pulse | `RepeatAnimation` scale pulse | P3 |
| Toast fade | `FadeTransition` auto-dismiss | P3 |

---

## Key Architecture Notes

### Type Patterns (Critical for new code)
```dart
// GameMode enum, NOT String
sortHand(cards, GameMode.hokum);

// Suit? for trump, NOT String?
isValidMove(card: c, hand: h, tableCards: tc, mode: m, trumpSuit: s, isLocked: false);

// AccountingEngine takes DoublingLevel enum
AccountingEngine.calculateRoundResult(
  usRaw: 80, themRaw: 82, usProjects: 20, themProjects: 0,
  bidType: 'SUN', doublingLevel: DoublingLevel.normal, bidderTeam: 'us',
);
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

### SocketService API (what exists vs what doesn't)
```dart
// EXISTS:
SocketService.instance.onConnectionStatus((status, attempt) {...});
SocketService.instance.onBotSpeak((text, speakerIdx) {...});
SocketService.instance.onGameUpdate((data) {...});

// DOES NOT EXIST YET (stubbed):
// onEmote, sendEmote, requestHint
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
| Widgets | 14 | ~3,200 |
| Screens | 3 | ~600 |
| Tests | 8 | ~1,500 |
| **Total** | **64** | **~11,600** |

## Git Status
```
main (ahead of origin by 4 commits):
  01a283f feat(M-F4): Core widgets & screens — GameScreen Stack, ActionDock, HandFan, HUD
  f3f2a69 feat(M-F3): State management — 17 Riverpod notifiers, 102 tests passing
  6d1cf8f feat(M-F2): Services layer — SocketService, AccountingEngine, state rotation, audio
  0dc4425 feat(M-F1): Flutter mobile app foundation — models, utils, theme, router
```

## Jules Status
- Session `9756301129946369522` FAILED (unknown error) — all 8 notifiers built manually
- No active Jules sessions

## Backend Tests (Unchanged)
- 550 tests passing (`python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`)
- 652 GBaloot tests passing
