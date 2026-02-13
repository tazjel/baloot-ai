# Next Session Missions — Detailed Task Plans

> **Generated**: 2026-02-13 14:11 | **Scan Results Below**

## 📊 Codebase Health Dashboard

| Metric | Value |
|--------|-------|
| Backend source files | 125 (game_engine: 45, ai_worker: 40, server: 40) |
| Frontend files | 95 (.tsx: 49, .ts: 46) |
| Test files | 76 (ratio: **0.61** ⚠️ — target 0.70) |
| Tests collected | **493** ✅ |
| Last Pass Rate | **100%** (493/493) ✅ |
| Last Code Coverage | **54.2%** ⚠️ |
| Last Test Run | 2026-02-13 14:09 |
| TypeScript errors | **0** ✅ |
| `as any` casts | **0** ✅ |
| Debug console.logs | **0** ✅ |
| TODO/FIXME/HACK | **2** (ai_worker/memory.py, ai_worker/mcts/utils.py) |

### Backend Hotspots (>15 KB)
| File | Size |
|------|------|
| `ai_worker/strategies/bidding.py` | 24.2 KB |
| `game_engine/logic/qayd_engine.py` | 21.4 KB |
| `ai_worker/strategies/components/hokum.py` | 20.8 KB |
| `game_engine/logic/game.py` | 19.8 KB |
| `ai_worker/strategies/components/sun.py` | 17.3 KB |
| `game_engine/logic/trick_manager.py` | 16.7 KB |
| `ai_worker/mcts/fast_game.py` | 16.2 KB |

### Frontend Hotspots (>10 KB)
| File | Size |
|------|------|
| `services/AccountingEngine.test.ts` | 18.2 KB |
| `services/AccountingEngine.ts` | 15.9 KB |
| `MatchReviewModal.tsx` | 15.4 KB |
| `ActionBar.tsx` | 15.3 KB |
| `hooks/useRoundManager.test.ts` | 14.3 KB |
| `Table.tsx` | 14.3 KB |
| `DisputeModal.tsx` | 13.9 KB |
| `table/GameArena.tsx` | 13.0 KB |
| `SettingsModal.tsx` | 11.8 KB |
| `App.tsx` | 11.7 KB |
| `services/botService.ts` | 11.3 KB |
| `hooks/useRoundManager.ts` | 11.1 KB |
| `hooks/useGameSocket.ts` | 10.6 KB |

---

## ✅ Completed Missions

### Mission 1: "The Architect" — State Consolidation Refactor ✅
> Merged via PR #9 on 2026-02-12

### Mission 5: "The Cleaner" — Code Hygiene Sprint ✅
> Completed 2026-02-12. All checks pass: 0 TS errors, 0 `as any`, 0 dead code, CODEBASE_MAP updated.

### Mission 3: "The Fixer" — Obsolete Test Cleanup ✅
> Completed 2026-02-12. Removed 52 obsolete tests. Full suite passes.

### Mission 7 Phase 1: Test Coverage Sprint ✅
> Completed 2026-02-13. Added 184 new tests (10 files). Suite: 493 passing. Ratio: 0.61.
> ⚠️ Found latent bug in `project_manager.py` get_proj_sig (crashes on multi-project hands).

### Mission 6: "The Surgeon" — Backend God-File Decomposition ✅
> Completed 2026-02-13 via Jules PR. Extracted: `qayd_state_machine.py`, `qayd_penalties.py`, `game_lifecycle.py`, `player_manager.py`, `trick_resolver.py`. Core files all reduced in size.

### Mission 12: "The Dashboard" — Test Manager Intelligence Center ✅ 🆕
> Completed 2026-02-13. Built full Test Manager tab in Command Center: coverage heatmap (pytest-cov), slow test detector, parallel execution (pytest-xdist), flaky tracker, run history with coverage trends. Fixed brain_view.py infinite rerun loop.

---

## 🎯 Active Missions

## Mission 11: "The Guardian" — Fix Latent Bugs
> Address known bugs discovered during testing (~1 hour)

### Tasks

- [ ] **Fix `project_manager.py` get_proj_sig** — crashes on multi-project hands (found during Mission 7)
- [ ] **Audit Qayd Engine edge cases** — `qayd_engine.py` (21 KB) still has complex state machine; verify penalty calculations at round boundaries
- [ ] **Server handler error paths** — `game_logger.py`, `sherlock_scanner.py` — verify graceful handling of malformed data

### Key Files
| File | Change |
|------|--------|
| `game_engine/logic/project_manager.py` | Fix get_proj_sig crash |
| `game_engine/logic/qayd_engine.py` | Audit penalty edge cases |
| `server/game_logger.py` | Error path hardening |

### Verification
```powershell
python -m pytest tests/game_logic/test_project_manager.py -v
python -m pytest tests/ -v --tb=short
```

---

## Mission 7 Phase 2: "The Shield" — Test Coverage to 70%
> Close the gap from 0.61 to 0.70 test ratio + boost code coverage from 54% → 70% (~2 hours)

### Tasks

- [ ] **Trick Manager Edge Cases** — Trump overtrump, void suit + forced play
- [ ] **Qayd Engine Coverage** — State transitions, penalty edge cases
- [ ] **Integration** — expand `verify_game_flow.py` for Sawa + multi-round
- [ ] **Server Tests** — Add tests for `bot_orchestrator.py`, `room_manager.py`, `socket_handler.py`
- [ ] **AI Worker Tests** — Add tests for `strategies/playing.py`, `sherlock.py`

### Key Files
| File | Change |
|------|--------|
| `tests/game_logic/test_trick_manager_unit.py` | New: trick edge cases |
| `tests/qayd/test_qayd_engine_unit.py` | New: state machine paths |
| `tests/server/test_orchestrator.py` | New: bot lifecycle |

### Verification
```powershell
python -m pytest tests/ --co -q  # verify count ≥88 files
python -m pytest tests/ --cov=game_engine --cov=server --cov=ai_worker --cov-report=term-missing
```

---

## Mission 10: "The Scalpel" — AI Worker God-File Decomposition
> Break the 3 largest ai_worker files into focused modules (~2 hours)

### Tasks

- [ ] **Split `bidding.py` (24 KB)** — largest file in the entire codebase
  - [ ] Extract Sun bidding logic → `strategies/components/sun_bidding.py`
  - [ ] Extract Hokum bidding logic → `strategies/components/hokum_bidding.py`
  - [ ] Keep `bidding.py` as thin router/orchestrator
- [ ] **Slim `hokum.py` (21 KB)**
  - [ ] Extract endgame tactics → `strategies/components/hokum_endgame.py`
  - [ ] Extract card counting helpers → shared utility
- [ ] **Slim `sun.py` (17 KB)**
  - [ ] Extract trump management → `strategies/components/sun_trump.py`

### Key Files
| File | Change |
|------|--------|
| `ai_worker/strategies/bidding.py` | Split into sun/hokum bidding modules |
| `ai_worker/strategies/components/hokum.py` | Extract endgame tactics |
| `ai_worker/strategies/components/sun.py` | Extract trump management |

### Verification
```powershell
python -m pytest tests/bot/ -v --tb=short
python -m pytest tests/ -v --tb=short
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
- [ ] **Split `AccountingEngine.ts` (16 KB)** — extract transaction logic vs. balance management
- [ ] **Split `MatchReviewModal.tsx` (15 KB)** — extract round detail & stat panels
- [ ] **Split `ActionBar.tsx` (15 KB)** — separate bidding and playing modes
- [ ] **Split `DisputeModal.tsx` (14 KB)** — already has dispute/ subfolder, move remaining logic
- [ ] **Split `GameArena.tsx` (13 KB)** — extract card layout logic

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
| `ai_worker/strategies/bidding.py` (24 KB) | Score-aware + project-aware bidding — also needs decomposition |
| `ai_worker/strategies/components/hokum.py` (21 KB) | Defensive play heuristics — needs decomposition |
| `ai_worker/strategies/components/sun.py` (17 KB) | Partner signaling |
| `ai_worker/strategies/playing.py` | Core play improvements |
| `ai_worker/memory.py` | Probabilistic memory TODO |

### Verification
```powershell
python -m pytest tests/bot/ -v
```

---

## 📊 Priority Matrix

| Mission | Impact | Effort | Risk | Order |
|---------|--------|--------|------|-------|
| **11. The Guardian** | 🔴 High | 🟢 Low | 🟢 Low | ① Bug Fixes |
| **7.2 The Shield** | 🔴 High | 🟡 Medium | 🟢 Low | ② Coverage to 70% |
| **10. The Scalpel** | 🔴 High | 🟢 Low | 🟡 Medium | ③ Hygiene |
| **8. The Polish** | 🔴 High | 🔴 High | 🟡 Medium | ④ UX |
| **9. The Strategist** | 🟡 Medium | 🔴 High | 🟡 Medium | ⑤ AI |
