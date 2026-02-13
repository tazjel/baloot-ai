# Next Session Missions — Detailed Task Plans

> **Generated**: 2026-02-13 03:15 | **Scan Results Below**

## 📊 Codebase Health Dashboard

| Metric | Value |
|--------|-------|
| Backend source files | 125 (game_engine: 45, ai_worker: 40, server: 40) |
| Frontend files | 95 (.tsx + .ts) |
| Test files | 76 (ratio: **0.61** tests per source file) ⬆️ |
| Tests passing | **492** ✅ |
| TypeScript errors | **0** ✅ |
| `as any` casts | **0** ✅ |
| Debug console.logs | **0** ✅ |
| TODO/FIXME/HACK | **2** (ai_worker/memory.py, ai_worker/mcts/utils.py) |

### Backend Hotspots (>15 KB)
| File | Size |
|------|------|
| `ai_worker/strategies/bidding.py` | 24.2 KB ⬆️ |
| `game_engine/logic/qayd_engine.py` | 21.4 KB ⬇️ |
| `ai_worker/strategies/components/hokum.py` | 20.8 KB ⬆️ |
| `game_engine/logic/game.py` | 19.8 KB ⬇️ |
| `ai_worker/strategies/components/sun.py` | 17.3 KB |
| `game_engine/logic/trick_manager.py` | 16.7 KB ⬇️ |
| `ai_worker/mcts/fast_game.py` | 16.2 KB |

### Frontend Hotspots (>10 KB)
| File | Size |
|------|------|
| `MatchReviewModal.tsx` | 15.4 KB ⬇️ |
| `ActionBar.tsx` | 15.3 KB |
| `Table.tsx` | 14.3 KB |
| `DisputeModal.tsx` | 13.9 KB |
| `GameArena.tsx` | 13.0 KB |
| `App.tsx` | 11.7 KB ⬇️ |
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
> Completed 2026-02-12. Removed 52 obsolete tests. Full suite passes.

### Mission 7 Phase 1: Test Coverage Sprint ✅
> Completed 2026-02-13. Added 184 new tests (10 files). Suite: 492 passing. Ratio: 0.61.
> ⚠️ Found latent bug in `project_manager.py` get_proj_sig (crashes on multi-project hands).

### Mission 6: "The Surgeon" — Backend God-File Decomposition ✅
> Completed 2026-02-13 via Jules PR. Extraction files created: `qayd_state_machine.py` (4.8 KB), `qayd_penalties.py` (1.1 KB), `game_lifecycle.py` (5.6 KB), `player_manager.py` (1.8 KB), `trick_resolver.py` (2.9 KB). Core files (`qayd_engine.py`, `game.py`, `trick_manager.py`) all reduced in size.

---

## 🎯 Active Missions

## Mission 7: "The Shield" — Test Coverage Expansion
> Close critical gaps in test coverage — ratio is 0.61, target 0.70

### Completed (2026-02-13)
- [x] `test_scoring_engine.py` — 18 tests (abnat, tiebreaks, Khasara, doubling)
- [x] `test_validation.py` — 14 tests (follow-suit, trump, Closed mode)
- [x] `test_contract_handler.py` — 26 tests (R1/R2, Ashkal, turns)
- [x] `test_sawa_manager.py` — 20 tests (eligibility, timing, declarations)
- [x] `test_bidding_integration.py` — 18 tests (full flows, serialization)
- [x] `test_doubling_handler.py` — 25 tests (Double→Gahwa chain, variant)
- [x] `test_akka_manager.py` — 17 tests (guards, eligibility, _card_key)
- [x] `test_project_manager.py` — 16 tests (SIRA/FIFTY/HUNDRED, resolution)
- [x] `test_game_lifecycle_unit.py` — 22 tests (start, deal, end_round)
- [x] `test_trick_resolver_unit.py` — 22 tests (card points, trick winner)

### Remaining Tasks
- [ ] **Trick Manager Edge Cases** — Trump overtrump, void suit + forced play
- [ ] **Qayd Engine Coverage** — State transitions, penalty edge cases
- [ ] **Integration** — expand `verify_game_flow.py` for Sawa + multi-round

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
- [ ] **Split `MatchReviewModal.tsx` (15 KB)** — extract round detail & stat panels
- [ ] **Split `ActionBar.tsx` (15 KB)** — separate bidding and playing modes
- [ ] **Split `DisputeModal.tsx` (14 KB)** — already has dispute/ subfolder, move remaining logic

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

## 📊 Priority Matrix

| Mission | Impact | Effort | Risk | Order |
|---------|--------|--------|------|-------|
| **7. The Shield** | 🔴 High | 🟡 Medium | 🟢 Low | ① Safety |
| **10. The Scalpel** | 🔴 High | 🟢 Low | 🟡 Medium | ② Hygiene |
| **8. The Polish** | 🔴 High | 🔴 High | 🟡 Medium | ③ UX |
| **9. The Strategist** | 🟡 Medium | 🔴 High | 🟡 Medium | ④ AI |
