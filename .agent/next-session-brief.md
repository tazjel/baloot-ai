# Next Session Missions — Detailed Task Plans

> **Generated**: 2026-02-17 | **Scan Results Below**

## 📊 Codebase Health Dashboard

| Metric | Value |
|--------|-------|
| Backend source files | **160** (game_engine: 46, ai_worker: 74, server: 40) |
| Frontend files | **106** (.tsx/.ts) |
| Test files | **86** |
| Test / Source Ratio | **0.54** (target: 0.70) ⚠️ |
| Last Pass Rate | **100%** (550/550) ✅ |
| Last Code Coverage | **53.9%** (target: 70%) ⚠️ |
| Last Test Run | 2026-02-17 |
| TypeScript `as any` | **1** ✅ (benign, `config.ts`) |
| `console.log` leaks | **0** ✅ (only in `devLogger.ts`) |
| TODO/FIXME/HACK | **3** (`memory.py`, `scout.py`, `verify_time_lord.py`) |

### Backend Hotspots (>15 KB)
| File | Size | Status |
|------|------|--------|
| `ai_worker/strategies/bidding.py` | ~17 KB | 🟢 Decomposed (M26: 4 focused methods) |
| `game_engine/logic/qayd_engine.py` | 21.4 KB | 🟡 Large |
| `game_engine/logic/game.py` | 20.4 KB | 🟡 Large |
| `ai_worker/bot_context.py` | 17.2 KB | 🟡 Large |
| `game_engine/logic/trick_manager.py` | 16.7 KB | 🟡 Unchanged |
| `ai_worker/mcts/fast_game.py` | 16.2 KB | 🟡 Unchanged |
| `ai_worker/strategies/components/hokum.py` | 15.8 KB | 🟡 Partially decomposed (was 32.8 KB) |

### Frontend Hotspots (>10 KB)
| File | Size | Status |
|------|------|--------|
| `components/SettingsModal.tsx` | 19.8 KB | 🔴 Critical |
| `services/SoundManager.ts` | 18.8 KB | 🔴 Critical |
| `services/AccountingEngine.test.ts` | 18.2 KB | 🟡 Test file |
| `components/ActionBar.tsx` | 17.2 KB | 🔴 Critical |
| `services/AccountingEngine.ts` | 15.9 KB | 🟡 Large |
| `components/MatchReviewModal.tsx` | 15.6 KB | 🟡 Large |
| `components/Table.tsx` | 14.8 KB | 🟡 Large |
| `hooks/useRoundManager.ts` | 11.8 KB | 🟡 Unchanged |
| `components/classic/ClassicArena.tsx` | 11.1 KB | 🟡 New |
| `services/hintService.ts` | 10.7 KB | 🟡 New |

---

## ✅ Completed Missions

### Mission 1: "The Architect" — State Consolidation Refactor ✅
> Merged via PR #9 on 2026-02-12

### Mission 3: "The Fixer" — Obsolete Test Cleanup ✅
> Completed 2026-02-12. Removed 52 obsolete tests.

### Mission 5: "The Cleaner" — Code Hygiene Sprint ✅
> Completed 2026-02-12. 0 TS errors, 0 dead code.

### Mission 6: "The Surgeon" — Backend God-File Decomposition ✅
> Completed 2026-02-13 via Jules PR. Core files reduced.

### Mission 7 Phase 1: Test Coverage Sprint ✅
> Completed 2026-02-13. +184 tests (10 files), suite: 493 passing.

### Mission 10: "The Scalpel" — AI Worker God-File Decomposition ✅
> Completed 2026-02-15. Extracted 4 new modules.

### Mission 11: "The Guardian" — Fix Latent Bugs ✅
> Completed 2026-02-14. +21 tests, 5 bugs fixed.

### Mission 12 (Original): "The Dashboard" — Test Manager Intelligence Center ✅
> Completed 2026-02-13. Built Dashboard Test Manager.

### Mission 12 (Redux): "Frontend Stability" — Fix Memory Leaks & Crashes ✅
> Completed 2026-02-14. Fixed 9 hooks with memory leaks.

### Mission 6 (Redux): "Test Fortress" — Expand Test Coverage ✅
> Completed 2026-02-14. +109 new tests (353→462).

### Mission 13: "The Contract" — Frontend Feature Gaps + Accessibility ✅
> Completed 2026-02-14. ARIA accessibility, Arabic labels, Kaboot banner.

### Mission 14: "The Fortress" — Server Security Hardening ✅
> Completed 2026-02-14. XSS, rate limiting, JWT, CORS.

### Mission 15: "The Consolidator" — Constants + Brain Wiring ✅
> Completed 2026-02-14. Shared `constants.py`, brain cascade wiring.

### Mission 16: "The Mind" — Bot Personality & Difficulty System ✅
> Completed 2026-02-14. 4 profiles, 4 difficulty levels, +40 tests.

### Mission 18: "The Showman" — Game Feel & Polish ✅
> Completed 2026-02-14. Sounds, dark mode, trump glow, animations.

### GBaloot Benchmark Lab ✅
> Completed 2026-02-15. Dual-engine comparison: 96.8% trick agreement.

### GBaloot Phase 2 (G5-G9) ✅
> Completed 2026-02-16. Full pipeline overhaul: 413 GBaloot + 502 main = 915 total tests.

### GBaloot Phase 3 — Autopilot Live Testing ✅
> Completed 2026-02-16. Live session: 1339 events, 100% decode rate, 634 game_states.

### Mobile Archive Parser & Benchmark ✅
> Completed 2026-02-16. 109 archives, 8,107 tricks, 100% engine agreement.

### Archive Rules Validation & Strategy Insights ✅
> Completed 2026-02-16. Full scoring + bidding validation across 109 archives.

### Scoring Formula Refinement — 100% Accuracy ✅
> Completed 2026-02-16. GP formulas refined to 100% agreement.

### Bidding Phase Documentation ✅
> Completed 2026-02-16. 12,291 bid events documented in KAMMELNA_SCHEMA.md.

### GBaloot Capture Session v2 — Workflow Improvements ✅
> Completed 2026-02-16. 5 capture pipeline improvements.

### Engine Reverse-Engineering (6 Missions) ✅
> Completed 2026-02-16. Full protocol decoded from 109 archive games.

### Empirical Data Mining (5 Missions) ✅
> Completed 2026-02-17. 109 pro games mined into 15 training files.

### Mission 9: "The Strategist" — Wire Empirical Data into Bot AI ✅
> Completed 2026-02-17. Pro data wired into 5 consumer modules.

### Mission 23 (Backend): God-File Decomposition ✅
> Completed 2026-02-17. hokum.py -52%, sun.py -58%.

### Mission 27: "The Accountant" — Scoring Engine Accuracy Overhaul ✅
> Completed 2026-02-17. Kammelna-validated formulas (100% on 1,095 rounds).
> SUN floor-to-even, HOKUM pair-based sum=16, khasara tie-break. +13 parametric tests.

### Mission 29: "The Reader" — Pro Follow-Play Pattern Mining ✅
> Completed 2026-02-17. 12,693 follow plays → 15 empirical constants.
> Calibrated follow_optimizer (trump threshold 10→15, seat-aware feed, second-hand-low).
> Calibrated brain (HIGH threshold 16→18, late-game boost). +17 tests.

---

### Mission 25: "The Release" — GitHub Release Preparation ✅
> Completed 2026-02-17. Secret scan clean, hardcoded path fixed, README/gitignore updated.

### Mission 26: "The Scalpel II" — Backend Hotspot Decomposition ✅
> Completed 2026-02-17. bidding.py get_decision() decomposed into 4 focused methods.
> 332-line monolith → clean orchestrator + _evaluate_hand_scores, _compute_thresholds,
> _apply_pro_frequency_validation, _make_final_decision.

### Mission 31: "The Conservator" — Trump Timing & Singleton Detection ✅
> Completed 2026-02-17. Pro trump conservation curve (43%→15.5%) wired into trump_manager.
> Singleton detection (10/A leads) in opponent_model. Discard signal reading in both
> opponent_model and partner_read. 15 new tests, 550 total passing.

## 🎯 Active Missions

### Mission 28: "The Oracle" — Endgame Solver Activation (Delegated to Jules)
> Fix hand reconstruction resilience, extend solver to 4 cards, validate against 2,728 pro endgame positions.

### Mission 30: "The Telepath" — Partner & Opponent Discard Signal Reading (Delegated to Jules)
> Add discard suit interpretation to partner_read.py and opponent_model.py. Shortest-suit discard in cooperative_play.py.

---

## Mission 23: "The Surgeon II" — God-File Decomposition (Frontend Remaining)
> Effort estimate (~2 hours) | Priority: ② — Structural hygiene

Backend ✅ complete. Frontend 3 critical hotspots remain.

### Tasks
- [ ] **Decompose `SettingsModal.tsx` (19.8 KB)** — extract theme/audio/game into sub-components
  - [ ] `SettingsThemeTab.tsx`, `SettingsAudioTab.tsx`, `SettingsGameTab.tsx`
- [ ] **Decompose `SoundManager.ts` (18.8 KB)** — extract sound definitions from player logic
  - [ ] `SoundRegistry.ts` (definitions) + `SoundPlayer.ts` (playback logic)
- [ ] **Decompose `ActionBar.tsx` (17.2 KB)** — separate bidding/playing action modes
  - [ ] `BiddingActions.tsx` + `PlayingActions.tsx`

### Key Files
| File | Change |
|------|--------|
| `components/SettingsModal.tsx` | Split → 3 tab components |
| `services/SoundManager.ts` | Split → registry + player |
| `components/ActionBar.tsx` | Split → bidding + playing |

### Verification
```powershell
npm run build  # No TS errors
python -m pytest tests/ --tb=short -q  # No backend regressions
```

### 🤖 Claude MAX Task (copy-paste ready)
```
Read frontend/src/components/SettingsModal.tsx completely.
Read frontend/src/services/SoundManager.ts completely.
Read frontend/src/components/ActionBar.tsx completely.

For each file:
1. Identify logical sub-sections that can be extracted
2. Create new component files for each section
3. Update the original file to import and compose the new components
4. Ensure all props and state are properly threaded through
5. Run `npm run build` to verify no TypeScript errors
```

---

## Mission 26: "The Scalpel II" — Backend Hotspot Decomposition ✅
> Completed 2026-02-17. bidding.py decomposed via internal method extraction.

---

## Mission 7 Phase 2: "The Shield" — Test Coverage to 70%
> Effort estimate (~3 hours) | Priority: ④ — Coverage gap

Test ratio is 0.54 (target 0.70), code coverage is 53.9% (target 70%). 6 tests failing.

### Tasks
- [ ] **Fix 6 Failing Tests** — investigate and fix (522 total, 516 passed)
- [ ] **Server Tests** — `bot_orchestrator.py`, `room_manager.py`, `socket_handler.py`
- [ ] **AI Worker Tests** — `strategies/playing.py`, `sherlock.py`
- [ ] **Trick Manager Edge Cases** — trump overtrump, void suit + forced play
- [ ] **Qayd Engine Coverage** — state transitions, penalty edge cases
- [ ] **Integration** — expand `verify_game_flow.py` for Sawa + multi-round

### Key Files
| File | Change |
|------|--------|
| `tests/server/test_orchestrator.py` | New: bot lifecycle |
| `tests/game_logic/test_trick_manager_unit.py` | New: trick edge cases |
| `tests/qayd/test_qayd_engine_unit.py` | New: state machine paths |

### Verification
```powershell
python -m pytest tests/ --cov=game_engine --cov=server --cov=ai_worker --cov-report=term-missing
```

### 🤖 Claude MAX Task (copy-paste ready)
```
Read game_engine/logic/trick_manager.py completely.
Read game_engine/logic/qayd_engine.py completely.
Read server/bot_orchestrator.py completely.
Read the test files in tests/game_logic/ and tests/qayd/ for patterns.

1. First, run existing tests to identify the 6 failures: python -m pytest tests/ -x --tb=short
2. Fix the failures
3. Then generate new test files for untested modules:
   - tests/server/test_orchestrator.py (bot lifecycle)
   - tests/game_logic/test_trick_manager_unit.py (edge cases)
4. Target: 70%+ code coverage on game_engine and server packages
5. Run full coverage report to verify
```

---

## Mission 24: "The Observer" — GBaloot Live Capture & Benchmark Sprint
> Effort estimate (~2 hours) | Priority: ⑤ — Empirical validation

### Tasks
- [ ] **Capture 3+ Hokum sessions** — `python gbaloot/capture_session.py --label hokum_study_01`
- [ ] **Capture 3+ Sun sessions** — same CLI, different labels
- [ ] **Run full benchmark** — decode → extract → compare
- [ ] **Analyze divergences** — document any engine disagreements
- [ ] **Update benchmark scorecard** — aim for ≥99% trick agreement

### Verification
- At least 6 capture sessions with WS data
- Divergence count documented

---

## Mission 8: "The Polish" — Frontend UX Sprint
> Effort estimate (~3 hours) | Priority: ⑥ — User experience

### Tasks
- [ ] **Card Play Animations** — animate cards from hand → table, trick-win sweep
- [ ] **Mobile Responsive** — audit at 375px and 768px
- [ ] **Remaining Frontend Decomposition**:
  - [ ] `AccountingEngine.ts` (15.9 KB) → extract transaction vs. balance
  - [ ] `MatchReviewModal.tsx` (15.6 KB) → extract round detail panels
  - [ ] `Table.tsx` (14.8 KB) → extract card layout

### Verification
- Playwright screenshots at 375px and 768px viewports
- No regressions in existing tests

---

## Mission 17: "The Teacher" — Interactive Tutorial & Learning Mode
> Effort estimate (~4 hours) | Priority: ⑦ — User onboarding

### Tasks
- [ ] **Tutorial System** — 7-lesson step-by-step guide
- [ ] **Hint System** — bid/play hints from bot AI
- [ ] **Practice Mode** — undo/redo, card reveal

---

## Mission 21: "The Brain Surgeon" — Advanced AI Intelligence
> Effort estimate (~4 hours) | Priority: ⑧ — Advanced AI

### Tasks
- [ ] **Probabilistic Memory** (Mind's Eye) — Bayesian card tracking
- [ ] **Score-Aware Engine** — dynamic risk/reward by score state
- [ ] **Endplay/Squeeze Detection** — advanced card play techniques
- [ ] **Partner Signaling** — lead strong suits to signal; track partner patterns
- [ ] **Sawa Timing** — claim only when certain

### 🤖 Claude MAX Task (copy-paste ready)
```
You are an expert Baloot player. Read these files:
- ai_worker/strategies/components/sun.py
- ai_worker/strategies/components/hokum.py
- ai_worker/strategies/components/cooperative_play.py
- ai_worker/signals/manager.py
- ai_worker/memory.py

1. Analyze the current partner signaling system
2. Design a Bayesian card tracking module that replaces the TODO in memory.py
3. Implement score-aware risk adjustment (conservative when ahead, aggressive when behind)
4. Write tests proving the improvement in decision quality
```

---

## Mission 19: "The Historian" — Match Replay & Statistics
> Effort estimate (~3 hours) | Priority: ⑨ — Engagement

### Tasks
- [ ] **Visual Replay** — playback controls, speed adjustment
- [ ] **Player Stats Dashboard** — win rate, favorite bids, trick accuracy
- [ ] **Achievements System** — milestones and badges

---

## Mission 20: "The Arena" — Multiplayer & Social Features
> Effort estimate (~5 hours) | Priority: ⑩ — Social

### Tasks
- [ ] **Room Browser** — lobby with room list, filters
- [ ] **Quick Match** — matchmaking system
- [ ] **Reconnection** — handle dropped connections gracefully
- [ ] **Spectator Mode** — watch live games

---

## Mission 22: "The Stage" — Production-Ready Game Experience
> Effort estimate (~5 hours) | Priority: ⑪ — Production

### Tasks
- [ ] **Arabic-First Localization** — RTL support, i18n
- [ ] **PWA/Offline Support** — service worker, offline play
- [ ] **Docker & CI/CD** — Dockerfiles, GitHub Actions pipeline
- [ ] **Code Splitting** — lazy load routes and heavy components

---

## 📊 Priority Matrix

| Mission | Impact | Effort | Risk | Order |
|---------|--------|--------|------|-------|
| **25. The Release** | 🔴 High | 🟢 Low | 🟢 Low | ① GitHub release prep |
| **23. Surgeon II** | 🟡 Medium | 🟢 Low | 🟢 Low | ② Frontend decomp |
| **26. Scalpel II** | 🟡 Medium | 🟡 Medium | 🟢 Low | ③ Backend decomp |
| **7.2 The Shield** | 🔴 High | 🟡 Medium | 🟢 Low | ④ Test coverage |
| **24. The Observer** | 🔴 High | 🟢 Low | 🟢 Low | ⑤ Live benchmark |
| **8. The Polish** | 🔴 High | 🟡 Medium | 🟢 Low | ⑥ UX Sprint |
| **17. The Teacher** | 🔴 High | 🔴 High | 🟡 Medium | ⑦ Tutorial |
| **21. Brain Surgeon** | 🟡 Medium | 🔴 High | 🟡 Medium | ⑧ Advanced AI |
| **19. The Historian** | 🟡 Medium | 🟡 Medium | 🟢 Low | ⑨ Replay/Stats |
| **20. The Arena** | 🟡 Medium | 🔴 High | 🔴 High | ⑩ Multiplayer |
| **22. The Stage** | 🟡 Medium | 🔴 High | 🟡 Medium | ⑪ Production |

## 🤖 Claude MAX Recommended Delegation

| Mission | Category | Why Claude |
|---------|----------|------------|
| **23. Surgeon II** (Frontend) | 🔴 Multi-File Refactor | 3 files → 8 files, component extraction |
| **26. Scalpel II** (bidding.py) | 🔴 Multi-File Refactor | Pattern-following decomposition |
| **7.2 The Shield** (Tests) | 🔵 Test Architecture | Bulk test generation, edge cases |
| **21. Brain Surgeon** | 🟢 Game-Theory Strategy | Claude can DESIGN the optimal approach |
