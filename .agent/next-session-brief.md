# Next Session Missions — Detailed Task Plans

> **Generated**: 2026-02-12 22:21 | **Scan Results Below**

## 📊 Codebase Health Dashboard

| Metric | Value |
|--------|-------|
| Backend source files | 119 (game_engine: 40, ai_worker: 39, server: 40) |
| Frontend files | 89 (.tsx + .ts) |
| Test files | 61 (ratio: **0.51** tests per source file) ⚠️ |
| TypeScript errors | **0** ✅ |
| `as any` casts | **0** ✅ |
| Debug console.logs | **0** ✅ (only in `devLogger.ts`) |
| TODO/FIXME/HACK | **2** (ai_worker/memory.py, ai_worker/mcts/utils.py) |

### Backend Hotspots (>15 KB)
| File | Size |
|------|------|
| `game_engine/logic/qayd_engine.py` | 23.2 KB |
| `game_engine/logic/game.py` | 22.6 KB |
| `ai_worker/strategies/bidding.py` | 19.4 KB |
| `game_engine/logic/trick_manager.py` | 17.7 KB |
| `ai_worker/strategies/components/hokum.py` | 16.7 KB |
| `ai_worker/mcts/fast_game.py` | 16.2 KB |
| `ai_worker/strategies/components/sun.py` | 16.1 KB |

### Frontend Hotspots (>10 KB)
| File | Size |
|------|------|
| `MatchReviewModal.tsx` | 18.3 KB |
| `ActionBar.tsx` | 15.3 KB |
| `Table.tsx` | 14.3 KB |
| `App.tsx` | 14.0 KB |
| `DisputeModal.tsx` | 13.9 KB |
| `GameArena.tsx` | 13.0 KB |
| `SettingsModal.tsx` | 11.8 KB |
| `botService.ts` | 11.3 KB |
| `useRoundManager.ts` | 11.1 KB |
| `useGameSocket.ts` | 10.6 KB |

---

## ✅ Completed Missions

### Mission 1: "The Architect" — State Consolidation Refactor ✅
> Merged via PR #9 on 2026-02-12

### Mission 5: "The Cleaner" — Code Hygiene Sprint ✅
> Completed 2026-02-12. All checks pass: 0 TS errors, 0 `as any`, 0 dead code, CODEBASE_MAP updated.

### Mission 3: "The Fixer" — Obsolete Test Cleanup ✅
> Completed 2026-02-12. Removed 52 obsolete tests referencing removed APIs. Full test suite now passes.

---

## 🎯 Active Missions

## Mission 6: "The Surgeon" — Backend God-File Decomposition
> Break the 3 largest backend files into focused modules (~3 hours)

### Tasks

- [ ] **Split `qayd_engine.py` (23 KB)**
  - [ ] Extract state transitions → `qayd_state_machine.py`
  - [ ] Extract penalty logic → `qayd_penalties.py`
  - [ ] Keep `qayd_engine.py` as thin orchestrator
- [ ] **Slim `game.py` (23 KB)**
  - [ ] Move remaining round-reset inline logic to `game_lifecycle.py`
  - [ ] Extract player management helpers → `player_manager.py`
- [ ] **Split `trick_manager.py` (18 KB)**
  - [ ] Extract trick resolution logic → `trick_resolver.py`
  - [ ] Extract trick validation → keep in `trick_manager.py`

### Key Files
| File | Change |
|------|--------|
| `game_engine/logic/qayd_engine.py` | Split into state machine + penalties |
| `game_engine/logic/game.py` | Extract lifecycle + player mgmt |
| `game_engine/logic/trick_manager.py` | Split resolution logic out |

### Verification
```powershell
python -m pytest tests/ -v --tb=short
python scripts/verification/run_serialization_guard.py
```

---

## Mission 7: "The Shield" — Test Coverage Expansion
> Close critical gaps in test coverage — ratio is 0.51, target 0.70 (~3 hours)

### Tasks

- [ ] **Trick Manager Edge Cases** — `tests/game_logic/test_trick_edge_cases.py`
  - [ ] Trump overtrump scenarios
  - [ ] Save high card when partner winning
  - [ ] Void suit + forced trump play
- [ ] **Project Scoring Combos** — `tests/features/test_project_scoring.py`
  - [ ] Multiple projects in same round
  - [ ] Akka + Project combo scoring
  - [ ] Project cancellation on contract loss
- [ ] **Timer/Timeout** — `tests/features/test_timer.py`
  - [ ] Timeout triggers bot autoplay
  - [ ] Timer reset on new trick
- [ ] **Qayd Engine Coverage** — `tests/qayd/test_qayd_engine_unit.py`
  - [ ] State transition paths (SCAN → CHALLENGE → VERDICT)
  - [ ] Penalty calculation edge cases
  - [ ] Timeout auto-dismiss
- [ ] **Integration** — expand `verify_game_flow.py`
  - [ ] Sawa claims resolve correctly
  - [ ] 3+ rounds complete without freeze

### Verification
```powershell
python -m pytest tests/ -v --tb=short
python -m pytest tests/ --co -q  # verify test count increased
```

---

## Mission 8: "The Polish" — Frontend UX Sprint
> Make the game feel alive and premium (~3 hours)

### Tasks

- [ ] **Card Play Animations**
  - [ ] Create `useCardAnimation.ts` hook
  - [ ] Animate cards entering table (scale + translate from player → center)
  - [ ] Trick-win sweep animation
- [ ] **Round Results Redesign**
  - [ ] Animated score counter in `RoundResultsModal.tsx`
  - [ ] Team color bars, winner crown animation
- [ ] **Sound Design**
  - [ ] Create `sounds/` directory (card-play, trick-win, bid-place, game-over)
  - [ ] Build `useSoundEffects.ts` hook with volume control
- [ ] **Mobile Responsive**
  - [ ] Audit at 375px and 768px widths
  - [ ] Fix card sizing, avatar positions, HUD overflow

### Frontend Decomposition Targets
- [ ] **Split `MatchReviewModal.tsx` (18 KB)** — largest component
- [ ] **Split `ActionBar.tsx` (15 KB)** — separate bidding and playing modes
- [ ] **Split `App.tsx` (14 KB)** — extract route/view logic to separate files

### Verification
- Playwright screenshots at card play, trick win, round end
- Playwright screenshots at 375px and 768px viewports

---

## Mission 9: "The Strategist" — Smarter Bot AI
> Make bots play like experienced Baloot players (~3 hours)

### Tasks

- [ ] **Partner Signaling** — lead strong suits to signal; track partner's played/avoided suits
- [ ] **Defensive Play** — cut trumps early vs opponent contracts; save cards when partner winning
- [ ] **Score-Aware Decisions** — increase aggression near game-end; risk vs reward by score
- [ ] **Project-Aware Play** — protect project cards; target opponent project cards
- [ ] **Sawa Timing** — claim only when 100% certain based on remaining cards
- [ ] **Address TODOs** — implement `memory.py` probabilistic memory upgrade; `mcts/utils.py` precise counting

### Key Files
| File | Change |
|------|--------|
| `ai_worker/strategies/bidding.py` (19 KB) | Score-aware + project-aware bidding |
| `ai_worker/strategies/components/hokum.py` (17 KB) | Defensive play heuristics |
| `ai_worker/strategies/components/sun.py` (16 KB) | Partner signaling |
| `ai_worker/strategies/playing.py` | Core play improvements |
| `ai_worker/memory.py` | Probabilistic memory TODO |

### Verification
```powershell
python -m pytest tests/bot/ -v
```

---

## Mission 10: "The Multiplayer" — Online Play Polish
> Make online mode production-ready (~4 hours)

### Tasks

- [ ] **Room Browser** — `/api/rooms` endpoint + `RoomBrowser.tsx`
- [ ] **Reconnection Handling** — 60s grace period, auto-restore seat, "Reconnecting..." overlay
- [ ] **Spectator Mode** — read-only join, see all 4 hands, hide ActionBar
- [ ] **In-Game Emotes** — Baloot-themed emotes (👏 يا حظك, 😤 حرام, 🔥 ماشاء الله)

### Key Files
| File | Change |
|------|--------|
| `frontend/src/components/RoomBrowser.tsx` | NEW — room listing UI |
| `server/socket_handler.py` | Reconnection + spectator events |
| `server/room_manager.py` | Disconnect timeout, spectator roles |

### Verification
- Multi-tab: create room + join from separate tabs
- Disconnect/reconnect within 60s
- Spectator view validation

---

## 📊 Priority Matrix

| Mission | Impact | Effort | Risk | Order |
|---------|--------|--------|------|-------|
| **6. The Surgeon** | 🔴 High | 🟡 Medium | 🟡 Medium | ① Next |
| **7. The Shield** | 🔴 High | 🟡 Medium | 🟢 Low | ② Safety |
| **8. The Polish** | 🔴 High | 🔴 High | 🟡 Medium | ③ UX |
| **9. The Strategist** | 🟡 Medium | 🔴 High | 🟡 Medium | ④ AI |
| **10. The Multiplayer** | 🔴 High | 🔴 High | 🔴 High | ⑤ Features |
