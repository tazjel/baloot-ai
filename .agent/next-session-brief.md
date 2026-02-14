# Next Session Missions — Detailed Task Plans

> **Generated**: 2026-02-14 (updated by Claude session 5) | **Scan Results Below**

## 📊 Codebase Health Dashboard

| Metric | Value |
|--------|-------|
| Backend source files | ~130 (game_engine: 45, ai_worker: 42, server: 42) |
| Frontend files | ~95 (.tsx: 49, .ts: 46) |
| Tests collected | **502** ✅ (bot + game_logic suites) |
| Last Pass Rate | **100%** (502/502) ✅ |
| Last Test Run | 2026-02-14 |
| TypeScript errors | **0** ✅ |
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

### Mission 12: "The Dashboard" — Test Manager Intelligence Center ✅
> Completed 2026-02-13. Built full Test Manager tab in Command Center.

### Mission 13: "The Contract" — Frontend Feature Gaps + Accessibility ✅
> Completed 2026-02-14. Added baloot/kaboot toast types, Kaboot banner in RoundResults, enhanced ScoreSheet tooltips (Arabic labels), ARIA accessibility across 6 modals + 10 icon buttons + 5 toggle switches.

### Mission 14: "The Fortress" — Server Security Hardening ✅
> Completed 2026-02-14. XSS sanitization (player names), rate limiting with Redis + memory fallback, room capacity limits (500), JWT secret validation, CORS configuration, error handler improvements.

### Mission 15: "The Consolidator" — Constants + Brain Wiring ✅
> Completed 2026-02-14. Created shared `constants.py` replacing 14+ duplicated files. Wired opponent_model into brain cascade (step 4). trick_review now adjusts brain threshold (0.4-0.6). Bayesian suit_probs fed into lead_selector + follow_optimizer. sun.py/hokum.py reordered for correct data flow.

---

## Mission 12 (New): "Frontend Stability" — Fix Memory Leaks & Crashes ✅
> Completed 2026-02-14. Fixed 9 hooks with memory leaks, stale closures, and timer issues. 0 TS errors.

### What Was Fixed
- **useGameToast.ts**: Toast auto-remove timers now tracked in Map ref, cleared on unmount + manual dismiss
- **useGameSocket.ts**: `gameUpdateCallbackRef` cleared on socket cleanup to prevent stale state updates
- **useBotSpeech.ts**: Added `isMountedRef` guard — socket callback + speech timers skip updates after unmount
- **useEmotes.ts**: Added `isMountedRef` guard — flying item timers skip state update if unmounted
- **useGameAudio.ts**: Cancel `window.speechSynthesis` on unmount to stop orphaned speech
- **useActionDispatcher.ts**: Added missing `handleCardPlay` to fast-forward effect dependency array
- **usePlayingLogic.ts**: Documented stable-ref deps with eslint-disable comment (offline mode timer)
- **useReplayNavigation.ts**: Removed `selectedTrickIdx` from interval deps — uses functional updater + ref to prevent interval churn
- **useShop.ts**: Flush pending debounced save on unmount using refs to prevent data loss

---

## Mission 6 (New): "Test Fortress" — Expand Test Coverage ✅
> Completed 2026-02-14. +109 new tests (353→462). All 6 subtasks done.

### What Was Added
- **test_baloot_declaration.py** (24 tests): Scan/no-scan, phase 1/2, points immunity, SUN mode exclusion, serialization, non-holder
- **test_scoring_integration.py** (29 tests): Full SUN/HOKUM rounds, Kaboot, Khasara flip, doubled/tripled, Gahwa, projects+tricks, tiebreak, last trick bonus, rounding, edge cases
- **test_strategy_modules.py** (23 tests): GalossGuard (6), CooperativePlay (5), FollowOptimizer (6), BidReader (6)
- **test_endgame_solver.py** (11 tests): 2/3-card minimax, trick resolution, empty/single hand, Kaboot pressure, partial/unknown hands fallback
- **test_bidding_edge_cases.py** (22 tests): Kawesh (4), phase transitions (7), serialization (4), input validation (4), score pressure (3)
- **test_round_trip.py** already comprehensive — no additions needed

---

## 🎯 Active Missions

## Mission 16: "The Mind" — Bot Personality & Difficulty System ✅
> Completed 2026-02-14. All 7 subtasks done. +40 tests (462→502).

### What Was Built
- **M16.1**: Expanded `personality.py` — 4 profiles (Saad/Khalid/Abu Fahad/Majed) with 7 playing attributes
- **M16.2**: Created `difficulty.py` — DifficultyLevel enum (EASY/MEDIUM/HARD/KHALID) with controlled mistakes
- **M16.3**: Created `personality_filter.py` — deceptive play, trump lead bias, point greed modifiers
- **M16.4**: Wired into `agent.py` — personality filter + difficulty noise after strategy, before legality check
- **M16.5**: Wired into `bidding.py` — bid_score_noise from difficulty, doubling_confidence from personality
- **M16.6**: Frontend difficulty selector in `Lobby.tsx` — 4-button grid (Arabic labels), flows through SocketService→room_lifecycle
- **M16.7**: Tests — `test_personality.py` (17 tests), `test_difficulty.py` (23 tests)

---

## Mission 11: "The Guardian" — Fix Latent Bugs ✅
> Completed 2026-02-14. 21 new tests added (332→353). All subtasks 11.1-11.5 done.

### What Was Fixed
- **project_manager.py**: `get_proj_sig` now handles Card objects, dicts, missing 'cards' key, non-list types
- **room_manager.py**: Replaced `redis_store.keys("game:*")` with `redis_store.scan()` in `clear_all_games()` and `games` property
- **bot_context.py**: Added empty hand guard in `get_legal_moves()` + added logger
- **agent.py**: Split catch-all exception into expected errors (ERROR) vs unexpected (CRITICAL)
- **game_actions.py**: Added BID payload type validation (action=str, suit∈♠♥♦♣) + turnDuration range check (1-120s)
- **is_kawesh_hand**: Now handles Card objects, dicts, empty/None hands via getattr + isinstance
- **Scoring engine**: 9 tests locking HOKUM rounding (.5→down, .6→up), SUN rounding, GP overflow, empty history

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

## New Game Improvement Missions (16-22)

### Mission 16: "The Mind" — Bot Personality & Difficulty System
> 4 bot personalities (Aggressive/Conservative/Tricky/Balanced) + 4 difficulty levels (Easy/Medium/Hard/Khalid)
> Key files: `ai_worker/strategies/personality.py` (new), `ai_worker/strategies/difficulty.py` (new), sun.py, hokum.py, bidding.py, frontend difficulty selector

### Mission 17: "The Teacher" — Interactive Tutorial & Learning Mode
> Step-by-step tutorial (7 lessons), hint system (bid/play hints from bot AI), practice mode with undo/redo and card reveal
> Key files: `frontend/src/components/Tutorial.tsx` (new), `frontend/src/hooks/useHintSystem.ts` (new), server hint API

### Mission 18: "The Showman" — Game Feel & Polish
> Card animations (deal/play/trick-win/Kaboot), expanded sound design, visual polish (felt texture, shadows, turn indicator), mobile responsive
> Key files: `frontend/src/hooks/useCardAnimation.ts` (new), SoundManager.ts, SettingsModal.tsx, index.css

### Mission 19: "The Historian" — Match Replay & Statistics
> Visual replay with playback controls, player stats dashboard, achievements, match export/share
> Key files: `frontend/src/services/StatsTracker.ts` (new), useReplayNavigation.ts, MatchReviewModal.tsx

### Mission 20: "The Arena" — Multiplayer & Social Features
> Room browser, private rooms, quick match, reconnection, spectator mode, quick chat, team chat, player profiles, XP/levels, leaderboard
> Key files: MultiplayerLobby.tsx, room_manager.py, socket_handler.py, EmoteMenu.tsx

### Mission 21: "The Brain Surgeon" — Advanced AI Intelligence
> Probabilistic memory (Mind's Eye), score-aware play engine, endplay/squeeze detection, self-play evaluation harness
> Key files: memory.py, `score_context.py` (new), endgame_solver.py, `scripts/self_play.py` (new)

### Mission 22: "The Stage" — Production-Ready Game Experience
> Arabic-first localization (RTL), code splitting, PWA/offline support, Dockerfiles, CI/CD pipeline
> Key files: `frontend/src/i18n/` (new), service worker, Dockerfiles (new), `.github/workflows/` (new)

---

## 📊 Priority Matrix

| Mission | Impact | Effort | Risk | Order |
|---------|--------|--------|------|-------|
| **11. The Guardian** | 🔴 High | 🟢 Low | 🟢 Low | ① Bug Fixes |
| **7.2 The Shield** | 🔴 High | 🟡 Medium | 🟢 Low | ② Coverage |
| **12. Frontend Stability** | 🔴 High | 🟡 Medium | 🟢 Low | ③ Stability |
| **16. The Mind** | 🔴 High | 🟡 Medium | 🟢 Low | ④ Bot Personality |
| **18. The Showman** | 🔴 High | 🔴 High | 🟡 Medium | ⑤ Game Feel |
| **17. The Teacher** | 🔴 High | 🔴 High | 🟡 Medium | ⑥ Tutorial |
| **7. Brain Expansion** | 🟡 Medium | 🟡 Medium | 🟡 Medium | ⑦ AI Wiring |
| **21. Brain Surgeon** | 🟡 Medium | 🔴 High | 🟡 Medium | ⑧ Advanced AI |
| **19. The Historian** | 🟡 Medium | 🟡 Medium | 🟢 Low | ⑨ Replay/Stats |
| **20. The Arena** | 🟡 Medium | 🔴 High | 🔴 High | ⑩ Multiplayer |
| **22. The Stage** | 🟡 Medium | 🔴 High | 🟡 Medium | ⑪ Production |
