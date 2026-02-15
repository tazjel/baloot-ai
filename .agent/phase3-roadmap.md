# GBaloot Phase 3 — Roadmap

> **Generated**: 2026-02-16 | **Status**: Ready for execution
> **Prerequisites**: Phase 2 complete (915 tests, 0 failures)

---

## Executive Summary

Phase 3 shifts from **building infrastructure** (Phase 1-2) to **hardening the system**: cleaning rule violations, removing dead code, expanding test coverage, and making GBaloot useful for continuous engine improvement. Seven missions (G10-G16), prioritized by impact and risk.

---

## G10: "The Janitor" — Constants & Rule Compliance Fix
> **Effort**: 30 min | **Risk**: Minimal | **Priority**: ① — Must do first

### Problem
CLAUDE.md states: *"All strategy modules import from constants.py — NO local constant definitions"*. Two files violate this:

### Tasks
- [ ] `ai_worker/strategies/components/point_density.py` lines 8-9 — Remove local `POINT_VALUES_SUN` and `POINT_VALUES_HOKUM`, import from `constants.py` (as `PTS_SUN`/`PTS_HOKUM`)
- [ ] `ai_worker/strategies/components/card_tracker.py` lines 14-18 — Remove local `ORDER_SUN`, `ORDER_HOKUM`, `SUITS`, `RANKS`, import from `constants.py`
- [ ] Verify no other files define local constants (grep entire `ai_worker/strategies/`)
- [ ] Run full test suite to confirm no regressions

### Files Changed
| File | Change |
|------|--------|
| `components/point_density.py` | Replace local dicts with imports |
| `components/card_tracker.py` | Replace local lists with imports |

### Verification
```
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q  # 502 pass
```

---

## G11: "The Mortician" — Dead Code Removal
> **Effort**: 1 hour | **Risk**: Low | **Priority**: ② — High value cleanup

### Problem
~1,400 LOC of dead code across 8 modules. Never activated in production play path. Adds confusion and maintenance burden.

### Active Play Path (Keep)
```
agent.get_decision()
  → PlayingStrategy.get_decision(ctx)
    → CognitiveOptimizer.get_decision(ctx)
      → MCTSSolver.search() + FastGame
    → SUN/HOKUM heuristics (fallback)
```

### Tasks
- [ ] **Remove** `ai_worker/strategies/neural.py` (~165 LOC) — NeuralStrategy never activates (no model file exists)
- [ ] **Remove** `ai_worker/professor.py` (~180 LOC) — Singleton instantiated but never called anywhere
- [ ] **Remove** `ai_worker/llm_client.py` (~150 LOC) — GeminiClient disabled, only referenced in dev scripts
- [ ] **Archive** `ai_worker/learning/` — Move to `ai_worker/_archived_learning/` with README explaining why:
  - `model.py` — StrategyNet architecture (no trained weights exist)
  - `feature_extractor.py` — 138-dim feature encoder (unused)
  - `train_network.py` — Training script (never runs in production)
  - `puzzle_generator.py` — Puzzle gen (Professor is dead)
  - `mind_reader.py` + `mind_utils.py` — Theory of Mind (no model file)
  - Keep `dataset_logger.py` in active code (used by CognitiveOptimizer, even if rarely triggered)
- [ ] **Deprecate** `ai_worker/mind_client.py` — Add deprecation warning, `BotContext.guess_hands()` fallback is sufficient
- [ ] **Clean** `ai_worker/strategies/playing.py` — Remove unused `neural_strategy` constructor param
- [ ] **Clean** `ai_worker/agent.py` — Remove neural_strategy instantiation and dead MCTS+neural paths
- [ ] Update imports across codebase to remove references to deleted modules
- [ ] Run full test suite

### Impact
- ~1,400 LOC removed
- Simpler agent.py (removes 3 dead code paths)
- Cleaner import tree

### Verification
```
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q  # 502 pass
grep -r "neural_strategy\|NeuralStrategy\|professor\|Professor\|llm_client\|GeminiClient" ai_worker/ --include="*.py"  # 0 matches
```

---

## G12: "The Surgeon III" — Strategy File Decomposition
> **Effort**: 2 hours | **Risk**: Low-Medium | **Priority**: ③ — Aligns with M23

### Problem
`hokum.py` (626 LOC) and `sun.py` (606 LOC) are the largest files in the codebase. Both implement identical patterns: 7-step brain cascade, lead selection, follow optimization, endgame. They also have extensive cross-imports (each imports from 8+ other components).

### Note on Cross-Imports
CLAUDE.md says components "must stay independent". However, `sun.py` and `hokum.py` are **orchestrators** (StrategyComponent classes), not pure-function leaf modules. Their cross-imports are architectural — they coordinate the other components. This is by design and should NOT be changed. The rule applies to leaf modules (e.g., `signaling.py` should not import from `opponent_model.py`).

`base.py` and `lead_preparation.py` also cross-import, but these are integration modules too (base provides shared endgame/discard, lead_preparation coordinates lead+bid reading).

### Tasks
- [ ] **Extract from hokum.py**: Create `hokum_follow.py` (~200 LOC) — HOKUM follow-suit logic (trump management, overtrump decisions)
- [ ] **Extract from hokum.py**: Create `hokum_lead.py` (~150 LOC) — HOKUM lead-specific strategy (trump extraction, suit establishment)
- [ ] **Slim hokum.py** to ~280 LOC orchestrator (dispatch to sub-modules)
- [ ] **Extract from sun.py**: Create `sun_follow.py` (~200 LOC) — SUN follow-suit logic (point dumping, partner support)
- [ ] **Extract from sun.py**: Create `sun_lead.py` (~150 LOC) — SUN lead-specific strategy (Ace leads, void creation)
- [ ] **Slim sun.py** to ~260 LOC orchestrator
- [ ] Run full test suite + bot strategy tests

### Impact
- hokum.py: 626 → ~280 LOC (-55%)
- sun.py: 606 → ~260 LOC (-57%)
- 4 new focused modules, each <200 LOC
- Easier to test individual lead/follow logic

### Verification
```
python -m pytest tests/bot/ --tb=short -q  # All strategy tests pass
```

---

## G13: "The Shield II" — Test Coverage Push
> **Effort**: 3 hours | **Risk**: Low | **Priority**: ④ — Coverage from 55% toward 70%

### Problem
52 modules have zero test coverage. Test/source ratio is 0.55 (target 0.70). Key untested areas: server routes, game phases, AI utilities.

### Tasks (Prioritized by Impact)
- [ ] **Game Engine Tests** (~40 new tests):
  - `test_trick_resolver.py` — Unit tests for trick resolution edge cases (trump overtrump, void + forced play, tie-breaking)
  - `test_autopilot.py` — Auto-play logic validation
  - `test_timer_manager.py` — Timer state machine tests
  - `test_referee.py` — Referee decision tests
- [ ] **AI Worker Tests** (~25 new tests):
  - `test_cognitive.py` — CognitiveOptimizer decision path (mock MCTS)
  - `test_playing_strategy.py` — PlayingStrategy dispatch logic
  - `test_agent.py` — BotAgent integration (mock game state)
- [ ] **Server Tests** (~20 new tests):
  - `test_socket_handler.py` — WebSocket message handling (mock connections)
  - `test_rate_limiter.py` — Rate limiting behavior
  - `test_game_logger.py` — Event logging verification
- [ ] **Strategy Module Tests** (~15 new tests):
  - `test_forensics.py` — ForensicScanner behavior
  - `test_discard_logic.py` — Discard selection tests
  - `test_hand_shape.py` — Distribution analysis
- [ ] Run full suite, target 600+ total tests

### Impact
- +100 new tests (502 → 600+)
- Test/source ratio: 0.55 → ~0.68
- Coverage of critical game engine paths

### Verification
```
python -m pytest tests/ --tb=short -q  # 600+ pass
python -m pytest tests/ --cov=game_engine --cov=ai_worker --cov-report=term-missing  # >65%
```

---

## G14: "The Classifier" — Divergence Root-Cause Engine
> **Effort**: 2 hours | **Risk**: Low | **Priority**: ⑤ — Makes GBaloot actionable

### Problem
All divergences are typed as "TRICK_WINNER" — no distinction between trump handling errors, rank order confusion, lead suit violations, or point miscalculations. This makes GBaloot divergences unactionable.

### Tasks
- [ ] **Extend Divergence model** in `comparator.py` — Add `root_cause` field (optional str):
  - `TRUMP_RANK` — Higher trump should have won
  - `TRUMP_CUT` — Trump should have beaten off-suit
  - `LEAD_SUIT_RANK` — Lead suit rank comparison error
  - `OFF_SUIT_DISCARD` — Off-suit card shouldn't affect winner
  - `UNKNOWN` — Can't determine root cause
- [ ] **Build classifier** in new `gbaloot/core/divergence_classifier.py`:
  - `classify_divergence(tc: TrickComparison) -> str` — Analyze cards, lead suit, trump suit to determine root cause
  - Uses card rank ordering from constants to determine which card *should* win
  - Compares engine vs source verdict to identify the disagreement type
- [ ] **Wire into comparator** — Auto-classify during `_compare_trick()`
- [ ] **Update Benchmark UI** — Add root-cause filter to Divergences tab
- [ ] **Update Analytics** — Show root-cause breakdown in Trend Summary
- [ ] Write 15+ tests for classifier

### Impact
- Divergences become actionable (know *what* to fix in engine)
- Analytics show patterns (e.g., "80% of divergences are TRUMP_RANK in HOKUM")
- Feeds directly into engine improvement priorities

### Verification
```
python -m pytest gbaloot/tests/test_divergence_classifier.py -v  # 15+ pass
```

---

## G15: "The Sentinel" — CI/CD Integration
> **Effort**: 1.5 hours | **Risk**: Low | **Priority**: ⑥ — Automation

### Problem
No automated testing on push/PR. No GBaloot regression detection. Tests only run manually.

### Tasks
- [ ] **Create `.github/workflows/tests.yml`** — Run on push to main and PRs:
  - Main test suite: `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`
  - GBaloot test suite: `python -m pytest gbaloot/tests/ --tb=short -q`
  - TypeScript check: `npx tsc --noEmit` (from frontend/)
  - Python version: 3.12
  - Node version: 20
- [ ] **Create `.github/workflows/benchmark.yml`** — Scheduled weekly:
  - Run GBaloot benchmark on all sessions
  - Export agreement % to artifact
  - Alert if agreement drops below 95%
- [ ] **Add test badges** to README (if exists)
- [ ] Verify workflows pass on GitHub

### Impact
- Automated regression detection on every push
- No more "did someone break the tests?" uncertainty
- Weekly benchmark ensures engine quality tracked over time

### Verification
Push to branch, verify GitHub Actions runs green.

---

## G16: "The Archivist" — Session Corpus & Regression Baseline
> **Effort**: 1.5 hours | **Risk**: Low | **Priority**: ⑦ — Data quality

### Problem
68 sessions of unknown quality. No curated "golden" test set. No regression baseline for engine changes.

### Tasks
- [ ] **Audit session corpus** — Run manifest builder on all 68 sessions, classify health
- [ ] **Curate golden set** — Select 10-15 "good" sessions with diverse game modes, complete rounds, known-correct winners. Save manifest as `gbaloot/data/golden_set.json`
- [ ] **Create regression test** — `gbaloot/tests/test_regression.py`:
  - Loads golden set sessions
  - Runs engine comparison
  - Asserts agreement % >= 95% per session
  - Fails loudly if any session drops below threshold
- [ ] **Document corpus** — Add README to `gbaloot/data/sessions/` explaining capture process, session naming, health classification
- [ ] **Corpus expansion guide** — Document how to capture new sessions (capture_session.py usage)
- [ ] Write 5+ regression tests

### Impact
- Engine changes can't silently break trick resolution
- Golden set provides regression safety net
- New sessions can be added to expand coverage

### Verification
```
python -m pytest gbaloot/tests/test_regression.py -v  # All golden sessions pass
```

---

## Phase 3 Priority Matrix

| Mission | Impact | Effort | Risk | Order | Dependencies |
|---------|--------|--------|------|-------|--------------|
| **G10: Janitor** | 🔴 High | 🟢 30m | 🟢 None | ① | None |
| **G11: Mortician** | 🔴 High | 🟢 1h | 🟢 Low | ② | None |
| **G12: Surgeon III** | 🔴 High | 🟡 2h | 🟡 Low-Med | ③ | G10 (clean constants first) |
| **G13: Shield II** | 🔴 High | 🟡 3h | 🟢 Low | ④ | G11 (less code to test) |
| **G14: Classifier** | 🟡 Medium-High | 🟡 2h | 🟢 Low | ⑤ | None |
| **G15: Sentinel** | 🟡 Medium | 🟢 1.5h | 🟢 Low | ⑥ | G13 (tests exist to automate) |
| **G16: Archivist** | 🟡 Medium | 🟢 1.5h | 🟢 Low | ⑦ | G14 (classifier enriches data) |

**Total estimated effort: ~12 hours**

---

## Expected Outcomes

| Metric | Current | After Phase 3 |
|--------|---------|---------------|
| Total tests | 915 | ~1,050+ |
| Dead code (LOC) | ~1,400 | ~0 |
| Constants violations | 2 files | 0 |
| Test/source ratio | 0.55 | ~0.68+ |
| CI/CD | Manual | Automated |
| Divergence classification | "TRICK_WINNER" only | 5 root-cause types |
| Regression safety | None | Golden set baseline |
| hokum.py LOC | 626 | ~280 |
| sun.py LOC | 606 | ~260 |

---

## What Phase 3 Does NOT Cover (Future Phases)

These are deferred to Phase 4+:
- **Frontend decomposition** (SoundManager 565 LOC, ActionBar 390 LOC) — M8/M23
- **Bot AI improvements** (partner signaling, defensive play) — M9
- **Tutorial system** — M17
- **Match replay** — M19
- **Multiplayer/Arena** — M20
- **Neural network training pipeline** (if ever needed) — M21
- **Production hardening** (Docker, i18n, PWA) — M22
- **MCTS legality bug investigation** — Requires FastGame audit
