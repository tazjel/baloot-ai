# Next Session Missions — Detailed Task Plans

> **Generated**: 2026-02-16 | **Scan Results Below**

## 📊 Codebase Health Dashboard

| Metric | Value |
|--------|-------|
| Backend source files | **155** (game_engine: 46, ai_worker: 69, server: 40) |
| Frontend files | **106** (.tsx/.ts) |
| Test files | **86** |
| Test / Source Ratio | **0.55** (target: 0.70) ⚠️ |
| Last Pass Rate | **100%** (1154/1154) — 502 main + 652 GBaloot ✅ |
| Last Code Coverage | **53.9%** (target: 70%) ⚠️ |
| Last Test Run | 2026-02-16 |
| TypeScript `as any` | **1** ✅ (benign, `config.ts`) |
| `console.log` leaks | **0** ✅ (only in `devLogger.ts`) |
| TODO/FIXME/HACK | **2** (ai_worker: `memory.py`, `mcts/utils.py`) |

### Backend Hotspots (>15 KB)
| File | Size | Status |
|------|------|--------|
| `ai_worker/strategies/components/hokum.py` | 32.8 KB | 🔴 Critical |
| `ai_worker/strategies/components/sun.py` | 29.1 KB | 🔴 Critical |
| `game_engine/logic/qayd_engine.py` | 21.4 KB | 🟡 Large |
| `game_engine/logic/game.py` | 20.4 KB | 🟡 Large |
| `ai_worker/strategies/bidding.py` | 19.2 KB | 🟡 Large |
| `ai_worker/bot_context.py` | 17.2 KB | 🟡 Large |
| `game_engine/logic/trick_manager.py` | 16.7 KB | 🟡 Unchanged |
| `ai_worker/mcts/fast_game.py` | 16.2 KB | 🟡 Unchanged |

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
| `services/hintService.ts` | 10.7 KB | 🟡 New |
| `components/classic/ClassicArena.tsx` | 11.1 KB | 🟡 New |
| `hooks/useRoundManager.ts` | 11.8 KB | 🟡 Unchanged |

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
> Completed 2026-02-16. Full pipeline overhaul:
> - G5: Reconstructor rewrite (SFS2X protocol, 43 tests)
> - G6: Session manifest + health classification (27 tests)
> - G7: Test Fortress Phase 2 + event types (74 tests)
> - G8: Match analytics + 7th Analytics tab (20 tests)
> - G9: Report exporter + download buttons (18 tests)
> - Final: 413 GBaloot + 502 main = 915 total tests, 0 failures

### GBaloot Phase 3 — Autopilot Live Testing ✅
> Completed 2026-02-16. End-to-end live pipeline validated:
> - StateBuilder: SFS2X events → BotAgent game_state, _resolve_command() for live routing
> - GBoard: JS injection actuator (SFS2X ExtensionRequest for card play/bid)
> - GBoard Recon: 10 JS probes, Blob-safe WS interceptor v4 (FileReader, no binaryType change)
> - Decoder: fixed keepalive 0x3F + JoinRoom two-pass identity bugs
> - Live session captured: 1339 events, 12 min, 100% decode rate, 634 game_states
> - 80 StateBuilder tests + 9 decoder tests = 995 total (502 main + 493 GBaloot)

### Mobile Archive Parser & Benchmark ✅
> Completed 2026-02-16. 109 mobile archives parsed, 100% engine agreement:
> - archive_parser.py: JSON loading, validation, bidding resolution (gm=3 ashkal = SUN)
> - archive_trick_extractor.py: Engine-computed trick winners (e=6 p field is NOT winner)
> - run_archive_benchmark.py: Full benchmark runner with scorecard output
> - 8,107 tricks across 1,095 rounds, 0 divergences, 100% point consistency
> - 48 new tests (17 parser + 31 extractor) = 1043 total (502 main + 541 GBaloot)

### Archive Rules Validation & Strategy Insights ✅
> Completed 2026-02-16. Full scoring + bidding validation across 109 archives:
> - archive_scoring_validator.py: GP conversion, khasara, kaboot (100%), radda doubling
> - archive_bidding_validator.py: 12,291 bid events, mode distribution
> - strategy_insights_from_archives.md: Actionable AI recommendations
> - 104 new tests = 1147 total (502 main + 645 GBaloot)

### Scoring Formula Refinement — 100% Accuracy ✅
> Completed 2026-02-16. Refined GP formulas to 100% agreement:
> - SUN GP: floor-to-even formula (q + 1 if q%2==1 and r>0)
> - HOKUM GP: pair-based rounding with sum=16 constraint
> - Khasara: bidder_gp < opp_gp, tie breaks by raw totals / doubler
> - Multiplier: derived from bid events, not em/m field

### Bidding Phase Documentation ✅
> Completed 2026-02-16. Comprehensive bidding rules extracted and documented:
> - scripts/tools/extract_bidding_patterns.py: 12,291 bid events analyzed
> - KAMMELNA_SCHEMA.md: +380 lines of bidding phase documentation
> - 12/12 verification rules passed: dealer rotation, ts mapping, ashkal, kawesh
> - Corrected ts field mapping (1=Hearts, 2=Clubs, 3=Diamonds, None=Spades, 4=placeholder)

### GBaloot Capture Session v2 — Workflow Improvements ✅
> Completed 2026-02-16. Built 5 improvements to the capture pipeline:
> - `capture_session.py`: Single-command CLI launcher with WS + screenshot capture
> - Event-triggered screenshots (bid, card played, trick won, round over)
> - Session labeling convention (`hokum_aggressive_01`, `sun_defensive_02`)
> - Post-session auto-pipeline (decode → extract → benchmark on exit)
> - `tools/screenshot_diff.py`: SSIM-based visual comparison utility
> - Enhanced `capturer.py` with `classify_event()` and `GAME_EVENT_KEYWORDS`

---

## 🎯 Active Missions

## Mission 23: "The Surgeon II" — AI Strategy File Decomposition
> Effort estimate (~2 hours) | Priority: ① — Low-risk hygiene

`hokum.py` = 32.8 KB and `sun.py` = 29.1 KB are the largest files in the codebase. Frontend hotspots `SettingsModal.tsx` (19.8 KB) and `ActionBar.tsx` (17.2 KB) also need splitting.

### Tasks
- [ ] **Decompose `hokum.py` (32.8 KB)** — extract trump management, defensive play, and partner coordination
  - [ ] Create `ai_worker/strategies/components/hokum_defense.py`
  - [ ] Create `ai_worker/strategies/components/hokum_trumping.py`
  - [ ] Reduce `hokum.py` to <15 KB orchestrator
- [ ] **Decompose `sun.py` (29.1 KB)** — extract suit management and cooperative logic
  - [ ] Create `ai_worker/strategies/components/sun_defense.py`
  - [ ] Create `ai_worker/strategies/components/sun_leading.py`
  - [ ] Reduce `sun.py` to <15 KB orchestrator
- [ ] **Decompose `SoundManager.ts` (18.8 KB)** — extract sound definitions from player logic
- [ ] **Decompose `SettingsModal.tsx` (19.8 KB)** — extract theme/audio/game sections into sub-components
- [ ] **Decompose `ActionBar.tsx` (17.2 KB)** — separate bidding/playing action modes

### Key Files
| File | Change |
|------|--------|
| `ai_worker/strategies/components/hokum.py` | Split into 3 files |
| `ai_worker/strategies/components/sun.py` | Split into 3 files |
| `frontend/src/services/SoundManager.ts` | Split definitions |
| `frontend/src/components/SettingsModal.tsx` | Extract sections |
| `frontend/src/components/ActionBar.tsx` | Extract modes |

### Verification
- All 522+ tests pass
- No new `as any` or `console.log` leaks
- All hotspot files <15 KB (backend) / <12 KB (frontend)

---

## Mission 7 Phase 2: "The Shield" — Test Coverage to 70%
> Effort estimate (~3 hours) | Priority: ② — Coverage gap

Test ratio is 0.55 (target 0.70), code coverage is 53.9% (target 70%), and 6 tests are currently failing.

### Tasks
- [ ] **Fix 6 Failing Tests** — investigate and fix the 6 failures (522 total, 516 passed)
- [ ] **Trick Manager Edge Cases** — Trump overtrump, void suit + forced play
- [ ] **Qayd Engine Coverage** — State transitions, penalty edge cases
- [ ] **Server Tests** — `bot_orchestrator.py`, `room_manager.py`, `socket_handler.py`
- [ ] **AI Worker Tests** — `strategies/playing.py`, `sherlock.py`
- [ ] **Integration** — expand `verify_game_flow.py` for Sawa + multi-round

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

## Mission 24: "The Observer" — GBaloot Live Capture & Benchmark Sprint
> Effort estimate (~2 hours) | Priority: ③ — Empirical validation

Run live capture sessions and benchmark against the engine. The new `capture_session.py` CLI is ready.

### Tasks
- [ ] **Capture 3+ Hokum sessions** — `python gbaloot/capture_session.py --label hokum_study_01`
- [ ] **Capture 3+ Sun sessions** — same CLI, different labels
- [ ] **Run full benchmark** — process captures through decode → extract → compare
- [ ] **Analyze divergences** — document any engine disagreements
- [ ] **Screenshot diff analysis** — `python gbaloot/tools/screenshot_diff.py --session <label>`
- [ ] **Update benchmark scorecard** — aim for ≥99% trick agreement

### Key Files
| File | Change |
|------|--------|
| `gbaloot/capture_session.py` | Launch point |
| `gbaloot/tools/screenshot_diff.py` | Post-capture analysis |
| `gbaloot/core/comparator.py` | Engine comparison |

### Verification
- At least 6 capture sessions with WS data
- Screenshot coverage of key game moments
- Divergence count documented

---

## Mission 8: "The Polish" — Frontend UX Sprint
> Effort estimate (~3 hours) | Priority: ④ — User experience

### Tasks
- [ ] **Card Play Animations** — animate cards from hand → table, trick-win sweep
  - [ ] Create `useCardAnimation.ts` hook
- [ ] **Mobile Responsive** — audit at 375px and 768px
  - [ ] Fix card sizing, avatar positions, HUD overflow
- [ ] **Frontend Decomposition** — split remaining hotspots:
  - [ ] `AccountingEngine.ts` (15.9 KB) → extract transaction vs. balance
  - [ ] `MatchReviewModal.tsx` (15.6 KB) → extract round detail panels
  - [ ] `Table.tsx` (14.8 KB) → extract card layout
  - [ ] `DisputeModal.tsx` (14.0 KB) → move logic to dispute/ subfolder

### Verification
- Playwright screenshots at 375px and 768px viewports
- No regressions in existing tests

---

## Mission 9: "The Strategist" — Smarter Bot AI
> Effort estimate (~3 hours) | Priority: ⑤ — Bot intelligence

### Tasks
- [ ] **Partner Signaling** — lead strong suits to signal; track partner patterns
- [ ] **Defensive Play** — cut trumps early vs opponent contracts
- [ ] **Score-Aware Decisions** — aggression near game-end
- [ ] **Sawa Timing** — claim only when certain
- [ ] **Address TODOs** — `memory.py` probabilistic memory, `mcts/utils.py` precise counting

### Key Files
| File | Change |
|------|--------|
| `ai_worker/strategies/components/hokum.py` | Defensive heuristics |
| `ai_worker/strategies/components/sun.py` | Partner signaling |
| `ai_worker/memory.py` | Probabilistic memory TODO |

### Verification
```powershell
python -m pytest tests/bot/ -v
```

---

## Mission 17: "The Teacher" — Interactive Tutorial & Learning Mode
> Effort estimate (~4 hours) | Priority: ⑥ — User onboarding

### Tasks
- [ ] **Tutorial System** — 7-lesson step-by-step guide
- [ ] **Hint System** — bid/play hints from bot AI
- [ ] **Practice Mode** — undo/redo, card reveal

### Key Files
| File | Change |
|------|--------|
| `frontend/src/components/Tutorial.tsx` | New |
| `frontend/src/hooks/useHintSystem.ts` | New |

---

## Mission 19: "The Historian" — Match Replay & Statistics
> Effort estimate (~3 hours) | Priority: ⑦ — Engagement

### Tasks
- [ ] **Visual Replay** — playback controls, speed adjustment
- [ ] **Player Stats Dashboard** — win rate, favorite bids, trick accuracy
- [ ] **Achievements System** — milestones and badges

---

## Mission 21: "The Brain Surgeon" — Advanced AI Intelligence
> Effort estimate (~4 hours) | Priority: ⑧ — Advanced AI

### Tasks
- [ ] **Probabilistic Memory** (Mind's Eye) — Bayesian card tracking
- [ ] **Score-Aware Engine** — dynamic risk/reward by score state
- [ ] **Endplay/Squeeze Detection** — advanced card play techniques
- [ ] **Self-Play Harness** — automated evaluation pipeline

---

## Mission 20: "The Arena" — Multiplayer & Social Features
> Effort estimate (~5 hours) | Priority: ⑨ — Social

### Tasks
- [ ] **Room Browser** — lobby with room list, filters
- [ ] **Quick Match** — matchmaking system
- [ ] **Reconnection** — handle dropped connections gracefully
- [ ] **Spectator Mode** — watch live games

---

## Mission 22: "The Stage" — Production-Ready Game Experience
> Effort estimate (~5 hours) | Priority: ⑩ — Production

### Tasks
- [ ] **Arabic-First Localization** — RTL support, i18n
- [ ] **PWA/Offline Support** — service worker, offline play
- [ ] **Docker & CI/CD** — Dockerfiles, GitHub Actions pipeline
- [ ] **Code Splitting** — lazy load routes and heavy components

---

## 📊 Priority Matrix

| Mission | Impact | Effort | Risk | Order |
|---------|--------|--------|------|-------|
| **23. Surgeon II** | 🔴 High | 🟢 Low | 🟢 Low | ① Decomposition |
| **7.2 The Shield** | 🔴 High | 🟡 Medium | 🟢 Low | ② Test Coverage |
| **24. The Observer** | 🔴 High | 🟢 Low | 🟢 Low | ③ Live Benchmark |
| **8. The Polish** | 🔴 High | 🟡 Medium | 🟢 Low | ④ UX Sprint |
| **9. The Strategist** | 🟡 Medium | 🟡 Medium | 🟡 Medium | ⑤ Bot AI |
| **17. The Teacher** | 🔴 High | 🔴 High | 🟡 Medium | ⑥ Tutorial |
| **19. The Historian** | 🟡 Medium | 🟡 Medium | 🟢 Low | ⑦ Replay/Stats |
| **21. Brain Surgeon** | 🟡 Medium | 🔴 High | 🟡 Medium | ⑧ Advanced AI |
| **20. The Arena** | 🟡 Medium | 🔴 High | 🔴 High | ⑨ Multiplayer |
| **22. The Stage** | 🟡 Medium | 🔴 High | 🟡 Medium | ⑩ Production |
