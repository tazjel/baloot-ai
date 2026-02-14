# Baloot AI — Strategic Roadmap

## Mission 1: Critical Bug Fixes (Est: 4-6 hours)
Priority: URGENT — These are correctness issues that affect gameplay

- [x] 1.1 Fix brain.py illegal card recommendations (filter by legal_indices)
- [x] 1.2 Implement `is_partner_winning()` in BotContext
- [x] 1.3 Fix defense_plan.py dead elif branch (line 56)
- [x] 1.4 Fix signaling.py LONE 10 RETURN dead code
- [x] 1.5 Fix point_density.py dead first loop in _classify
- [x] 1.6 Fix sun.py partner_pos potential NameError
- [x] 1.7 Fix deserialization to restore AkkaManager/SawaManager
- [x] 1.8 Fix dealer rotation persistence across rounds

## Mission 2: Wire the Disconnected Brain (Est: 8-12 hours)
Priority: HIGH — Activates ~1000 lines of already-written analysis code

- [x] 2.1 Wire opponent_model output into lead_selector + brain.py cascade
- [x] 2.2 Wire trick_review output into strategy aggression adjustment
- [x] 2.3 Use Bayesian probabilities for trump count estimation
- [x] 2.4 Use trick_projection in actual bid decisions (not just logging)
- [x] 2.5 Pass void_suits to defense_plan from CardTracker
- [x] 2.6 Build heuristic hand reconstruction for endgame solver (no ML needed)

## Mission 3: Bidding Phase Improvements (Est: 6-8 hours)
Priority: HIGH — Directly affects win rate

- [x] 3.1 Integrate floor card into Hokum strength calculation
- [x] 3.2 Add defensive bidding inference (use opponent bid info)
- [x] 3.3 Calibrate SUN scoring to prevent over-bidding
- [x] 3.4 Make trick count a graduated factor in bid decisions (loser penalty, min tricks, floor card in projection)
- [x] 3.5 Fix hand_shape patterns for 8-card Baloot distributions (was using 13-card Bridge patterns!)

## Mission 4: Playing Phase Strategic Depth (Est: 12-16 hours)
Priority: HIGH — Biggest competitive differentiator

- [x] 4.1 Trump timing engine (phased: PARTIAL_DRAW → CASH_SIDES → FINISH)
- [x] 4.2 Bidding inference during play (bid_reader.py card reading from bid history)
- [x] 4.3 Entry management system (ENTRY_TRANSFER + VOID_ENTRY in cooperative_play)
- [x] 4.4 Second-hand-low / fourth-hand-high discipline (follow_optimizer positional play)
- [x] 4.5 Galoss awareness + emergency defensive mode (galoss_guard.py)
- [x] 4.6 Cooperative point feeding (tiered A/10 + K/Q feeding + off-suit feeding)

## Mission 5: Game Engine Completeness (Est: 6-8 hours)
Priority: MEDIUM — Missing features

- [x] 5.1 Implement Baloot declaration (K+Q of trump = 20 Abnat / 2 GP, two-phase: Baloot → Re-baloot)
- [x] 5.2 Verify Kaboot point values (SUN=44, HOKUM=25 confirmed correct per pagat.com)
- [x] 5.3 Fix dead stubs in core/rules.py (_get_current_winner_card, _can_beat_trump, _compare_cards — all implemented)
- [x] 5.4 Add scoring constants to canonical constants.py (KABOOT_GP, BALOOT_GP, TOTAL_ABNAT, MATCH_TARGET etc.)

## Mission 6: Test Coverage Expansion (Est: 8-10 hours)
Priority: MEDIUM — Quality assurance

- [ ] 6.1 Add tests for all Mission 1 bug fixes
- [ ] 6.2 Add integration tests for wired modules (Mission 2)
- [ ] 6.3 Add bidding edge case tests (borderline hands, floor card)
- [ ] 6.4 Add endgame solver tests with known positions
- [ ] 6.5 Add game serialization/deserialization round-trip tests
- [ ] 6.6 Add WebSocket handler tests

## Mission 7: Production Hardening (Est: 10-14 hours)
Priority: MEDIUM — Required for deployment

- [ ] 7.1 Replace hardcoded JWT secret with env variable
- [ ] 7.2 Fix CORS to whitelist specific origins
- [ ] 7.3 Add WebSocket message validation (schema)
- [ ] 7.4 Add Dockerfile + production Docker Compose
- [ ] 7.5 Add GitHub Actions CI pipeline (test → lint → build)
- [ ] 7.6 Add database migrations (Alembic)

## Mission 8: Competitive Edge Features (Est: 16-20 hours)
Priority: LOW — Polish and advanced AI

- [ ] 8.1 Suit combination probability tables
- [ ] 8.2 Safety play vs maximum play optimizer
- [ ] 8.3 Squeeze/endplay detection in endgame
- [ ] 8.4 Personality-based play styles (aggressive/defensive/tricky)
- [ ] 8.5 Self-play training loop (bots vs bots, auto-tune thresholds)
- [ ] 8.6 ELO rating system for bot difficulty levels

---
**Total Estimated Effort: 70-94 hours across all missions**
**Critical Path (Missions 1-4): 30-42 hours**
