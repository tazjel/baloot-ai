# GBaloot Phase 3 — Pre-Roadmap Analysis

> Generated: 2026-02-16 | Status: Analysis complete, roadmap pending

## Codebase Deep Dive Results

### Backend Hotspots (>15KB)
| File | LOC | Risk |
|------|-----|------|
| hokum.py | 626 | HIGH — needs decomposition |
| sun.py | 606 | HIGH — needs decomposition |
| qayd_engine.py | 475 | MEDIUM — delegates properly |
| bidding.py | 405 | MEDIUM |
| game.py | 402 | PROTECTED — do not modify |
| fast_game.py | 402 | MEDIUM |
| bot_context.py | 400 | HIGH — large wrapper |
| trick_manager.py | 370 | MEDIUM |
| rules_validator.py | 352 | MEDIUM — overlaps validation.py |
| validation.py | 333 | MEDIUM — overlaps rules_validator.py |

### Critical Issues Found
1. **Duplicate constants** — `discard_logic.py` and `card_tracker.py` define local ORDER/POINT_VALUES (violates CLAUDE.md)
2. **MCTS bug** — `professor.py:78` logs "MCTS considers ILLEGAL move" at runtime
3. **Dead code** — neural.py, learning/ module (742 LOC), MCTS (850+ LOC) all disconnected
4. **52 untested modules** — especially server routes, learning pipeline, game phases

### Test Coverage Gaps (Critical)
- Server: auth, brain, game, qayd, puzzles routes — 0 tests
- AI: neural.py, sherlock.py, cognitive.py — 0 tests
- Game: autopilot.py, referee.py, trick_resolver.py, timer_manager.py — 0 tests
- Learning: entire module (model, feature_extractor, train_network) — 0 tests
- MCTS: mcts.py, utils.py — 0 tests

### Frontend Hotspots (>12KB)
| File | LOC |
|------|-----|
| SoundManager.ts | 565 |
| ActionBar.tsx | 390 |
| Table.tsx | 376 |
| App.tsx | 372 |
| ClassicBoard.tsx | 363 |

### GBaloot Status
- All modules tested, 413 tests, 0 failures
- No broken imports
- 96.8% trick agreement
- Phase 2 fully complete (G5-G9)

## Phase 3 Direction Notes
- Priority 1: Constants violation fix (quick win, rule compliance)
- Priority 2: sun.py/hokum.py decomposition (M23 from mission brief)
- Priority 3: Test coverage push toward 70% target
- Priority 4: Frontend file decomposition
- Priority 5: GBaloot — live capture improvements, more sessions for benchmark
- Phase 3 roadmap to be built on reconnect
