# Baloot AI — Strategic Roadmap

## Mission 1: Critical Bug Fixes ✅
Priority: URGENT — These are correctness issues that affect gameplay

- [x] 1.1 Fix brain.py illegal card recommendations (filter by legal_indices)
- [x] 1.2 Implement `is_partner_winning()` in BotContext
- [x] 1.3 Fix defense_plan.py dead elif branch (line 56)
- [x] 1.4 Fix signaling.py LONE 10 RETURN dead code
- [x] 1.5 Fix point_density.py dead first loop in _classify
- [x] 1.6 Fix sun.py partner_pos potential NameError
- [x] 1.7 Fix deserialization to restore AkkaManager/SawaManager
- [x] 1.8 Fix dealer rotation persistence across rounds

## Mission 2: Wire the Disconnected Brain ✅
Priority: HIGH — Activates ~1000 lines of already-written analysis code

- [x] 2.1 Wire opponent_model output into lead_selector + brain.py cascade
- [x] 2.2 Wire trick_review output into strategy aggression adjustment
- [x] 2.3 Use Bayesian probabilities for trump count estimation
- [x] 2.4 Use trick_projection in actual bid decisions (not just logging)
- [x] 2.5 Pass void_suits to defense_plan from CardTracker
- [x] 2.6 Build heuristic hand reconstruction for endgame solver (no ML needed)

## Mission 3: Bidding Phase Improvements ✅
Priority: HIGH — Directly affects win rate

- [x] 3.1 Integrate floor card into Hokum strength calculation
- [x] 3.2 Add defensive bidding inference (use opponent bid info)
- [x] 3.3 Calibrate SUN scoring to prevent over-bidding
- [x] 3.4 Make trick count a graduated factor in bid decisions (loser penalty, min tricks, floor card in projection)
- [x] 3.5 Fix hand_shape patterns for 8-card Baloot distributions (was using 13-card Bridge patterns!)

## Mission 4: Playing Phase Strategic Depth ✅
Priority: HIGH — Biggest competitive differentiator

- [x] 4.1 Trump timing engine (phased: PARTIAL_DRAW → CASH_SIDES → FINISH)
- [x] 4.2 Bidding inference during play (bid_reader.py card reading from bid history)
- [x] 4.3 Entry management system (ENTRY_TRANSFER + VOID_ENTRY in cooperative_play)
- [x] 4.4 Second-hand-low / fourth-hand-high discipline (follow_optimizer positional play)
- [x] 4.5 Galoss awareness + emergency defensive mode (galoss_guard.py)
- [x] 4.6 Cooperative point feeding (tiered A/10 + K/Q feeding + off-suit feeding)

## Mission 5: Game Engine Completeness ✅
Priority: MEDIUM — Missing features

- [x] 5.1 Implement Baloot declaration (K+Q of trump = 20 Abnat / 2 GP, two-phase: Baloot → Re-baloot)
- [x] 5.2 Verify Kaboot point values (SUN=44, HOKUM=25 confirmed correct per pagat.com)
- [x] 5.3 Fix dead stubs in core/rules.py (_get_current_winner_card, _can_beat_trump, _compare_cards — all implemented)
- [x] 5.4 Add scoring constants to canonical constants.py (KABOOT_GP, BALOOT_GP, TOTAL_ABNAT, MATCH_TARGET etc.)

---

## Mission 6: Test Fortress (Est: 8-10 hours)
Priority: HIGH — Confidence in correctness before shipping

### 6.1 Baloot Declaration Tests
Write dedicated test suite `tests/game_logic/test_baloot_manager.py`:
- [ ] 6.1a **Basic Baloot flow**: Deal K+Q of trump to player, play K first → BALOOT announced, play Q → RE_BALOOT declared, verify 2 GP awarded post-doubling
- [ ] 6.1b **Doubling immunity**: Baloot + Dobl(2x) → verify Baloot GP stays 2, not 4. Same for Khamsin(3x), Raba'a(4x)
- [ ] 6.1c **Project blocking**: Player has 100-project containing K+Q of trump → Baloot should NOT be declared
- [ ] 6.1d **Both teams Baloot**: Team A has K+Q of ♠ trump, Team B has... (impossible in Hokum, but test graceful handling)
- [ ] 6.1e **Serialization round-trip**: Game with active Baloot phase1 → serialize → deserialize → phase still tracked

### 6.2 Scoring Engine Integration Tests
Write `tests/game_logic/test_scoring_integration.py`:
- [ ] 6.2a **Full SUN round**: Simulate 8 tricks with known cards, verify Abnat = 130, GP = 26 total
- [ ] 6.2b **Full HOKUM round**: 8 tricks, verify Abnat = 162, GP = 16 total
- [ ] 6.2c **Kaboot SUN**: One team wins all 8 → 44 GP (not 26)
- [ ] 6.2d **Kaboot HOKUM**: One team wins all 8 → 25 GP (not 16)
- [ ] 6.2e **Khasara flip**: Bidder team gets fewer GP → bidder gets 0, defender gets all
- [ ] 6.2f **Doubling + Khasara combo**: Doubled game where bidder loses → verify doubled penalty
- [ ] 6.2g **Gahwa scoring**: Level=100, opponent shut out → 152 GP awarded
- [ ] 6.2h **Projects + tricks**: Team has Sira(2 GP) + 14 GP tricks = 16 GP total in HOKUM

### 6.3 Strategy Module Tests
Write `tests/bot/test_strategy_modules.py`:
- [ ] 6.3a **galoss_guard**: At trick 5 with 3 tricks won (buyer) → risk_level=HIGH, emergency_mode=True
- [ ] 6.3b **galoss_guard defender**: Defender pressing → GALOSS_PRESS recommendation
- [ ] 6.3c **cooperative_play entry transfer**: Partner strong in ♥, I have low ♥ → recommends lead low ♥
- [ ] 6.3d **follow_optimizer SECOND_HAND_LOW**: Seat 2, low-value trick → plays cheapest legal card
- [ ] 6.3e **follow_optimizer FOURTH_HAND_HIGH**: Seat 4, can win cheaply → wins with minimum winning card
- [ ] 6.3f **follow_optimizer FEED_PARTNER**: Partner winning, I have A♠ → feeds A for points
- [ ] 6.3g **bid_reader inference**: Opponent bid Hokum ♠ → infer strong ♠ holding

### 6.4 Endgame Solver Tests
Write `tests/bot/test_endgame_solver.py`:
- [ ] 6.4a **2-card SUN endgame**: Known hands, verify optimal play found
- [ ] 6.4b **3-card HOKUM endgame**: Trump remaining, verify trump timing correct
- [ ] 6.4c **Heuristic hand reconstruction**: Given trick history, verify guessed hands are plausible
- [ ] 6.4d **Endgame with Kaboot pressure**: Team at 7 tricks, last card decides sweep

### 6.5 Serialization Round-Trip Tests
Expand `tests/game_logic/test_round_trip.py`:
- [ ] 6.5a **Mid-bidding serialize**: Game in BIDDING phase → round-trip → bidding_engine state preserved
- [ ] 6.5b **Mid-trick serialize**: 2 cards on table → round-trip → table_cards + current_turn correct
- [ ] 6.5c **Qayd active serialize**: Qayd challenge in progress → round-trip → qayd_state preserved
- [ ] 6.5d **Full match history**: Multiple rounds completed → round-trip → past_round_results intact

### 6.6 Bidding Edge Cases
Write `tests/bot/test_bidding_edge_cases.py`:
- [ ] 6.6a **Zero-point hand Kawesh**: Hand with 0 card points → bot requests Kawesh
- [ ] 6.6b **Floor card Ace trap**: Floor card is A♠ but hand has no J♠ or 9♠ → bot avoids Hokum ♠
- [ ] 6.6c **Borderline SUN hand**: Score exactly at threshold → verify bid/pass decision
- [ ] 6.6d **Last speaker forced bid**: R2 last speaker, no one bid → must bid
- [ ] 6.6e **Ashkal detection**: 4 Aces in hand + dealer → triggers Ashkal SUN
- [ ] 6.6f **Score pressure desperate**: Behind 140-50 → lower thresholds, more aggressive bids

---

## Mission 7: Brain Expansion (Est: 10-12 hours)
Priority: HIGH — The brain only uses 6/28 modules; this is the biggest AI win

### 7.1 Opponent Model Integration (Currently Orphaned)
opponent_model computes `combined_danger`, `safe_lead_suits`, `avoid_lead_suits` but no module reads them.
- [ ] 7.1a **Wire into lead_selector**: Pass `avoid_lead_suits` as negative filter in lead choice. If opponent is STRONG in a suit (danger > 0.7), avoid leading it unless we have master card
- [ ] 7.1b **Wire into defense_plan**: When opponent danger is HIGH, shift defense_plan to protect that suit specifically (e.g., don't discard guards)
- [ ] 7.1c **Wire into brain.py cascade**: Add opponent_model as priority level between defense_plan and partner_signal. If danger > 0.8, override with AVOID recommendation (conf 0.65)
- [ ] 7.1d **Test**: Create scenarios with known opponent strength → verify bot avoids dangerous leads

### 7.2 Trick Review Integration (Currently Orphaned)
trick_review computes `momentum`, `strategy_shift`, `avoid_suits` but only `strategy_shift` threshold adjustment is used.
- [ ] 7.2a **Wire momentum into aggression**: If momentum = "losing" and tricks_behind >= 2, raise aggression_threshold by 0.15 (more desperate plays)
- [ ] 7.2b **Wire avoid_suits into lead_selector**: Pass trick_review's `avoid_suits` alongside opponent_model's avoid list
- [ ] 7.2c **Wire strategy_shift into cooperative_play**: If shift = "conservative", reduce feeding aggression; if "aggressive", increase entry transfer frequency
- [ ] 7.2d **Test**: Simulate losing position → verify bot shifts to aggressive recovery mode

### 7.3 Brain Cascade Expansion
Currently brain.py only handles LEAD decisions for 6 modules. Expand scope.
- [ ] 7.3a **Add follow-suit cascade**: brain.py currently skips follow decisions entirely (goes straight to follow_optimizer). Add a brain_follow() that can override with trump_manager HOLD_TRUMP or defense_plan PROTECT recommendations
- [ ] 7.3b **Lower confidence threshold**: Current 0.7 is too conservative — brain recommendations get rejected ~60% of the time. Lower to 0.55 for lead, 0.50 for follow
- [ ] 7.3c **Add galoss_guard to cascade**: When galoss risk is CRITICAL, brain should override ALL other modules (conf 0.95)
- [ ] 7.3d **Add score_pressure awareness**: Use match score differential to shift the entire cascade. When desperate (behind 100+), lower all thresholds by 0.1. When winning (ahead 100+), raise by 0.1 (more conservative)
- [ ] 7.3e **Test**: Verify cascade priority order still respects legal_indices filtering

### 7.4 Bayesian Probability Usage
CardMemory builds Bayesian suit probabilities per player, but strategies mostly ignore them.
- [ ] 7.4a **Wire into lead_selector PARTNER_LEAD**: If P(partner has suit X) > 0.7, lead X even without signal confirmation
- [ ] 7.4b **Wire into trump_manager**: If P(opponents have trump) < 0.2, skip trump draw phase (trumps already out)
- [ ] 7.4c **Wire into follow_optimizer WIN_CHEAP**: If P(next player has suit) < 0.3, can be less aggressive about winning
- [ ] 7.4d **Wire into endgame_solver**: Replace uniform random with Bayesian priors for opponent hand estimation

### 7.5 Score-Aware Play Adaptation
score_differential exists in BotContext but is only used in bidding. Playing strategy should adapt.
- [ ] 7.5a **Implement score_context module**: Pure function `get_score_context(team_scores, match_scores)` → returns {phase: "EARLY"/"MID"/"LATE"/"MATCH_POINT", aggression_modifier: float, risk_tolerance: float}
- [ ] 7.5b **Wire into brain.py**: Multiply all confidence thresholds by `risk_tolerance` (1.0 = normal, 0.8 = risky/desperate, 1.2 = safe/conservative)
- [ ] 7.5c **Wire into kaboot_pursuit**: At MATCH_POINT, always attempt Kaboot if feasible (even with low probability)
- [ ] 7.5d **Test**: Bot at 148 match points → plays ultra-conservative to secure win

---

## Mission 8: Constants & Architecture Cleanup (Est: 4-6 hours)
Priority: MEDIUM — Technical debt that compounds

### 8.1 Centralize Strategy Constants
ORDER_SUN, ORDER_HOKUM, PTS_SUN, PTS_HOKUM are duplicated across 12+ strategy files.
- [ ] 8.1a **Create `ai_worker/strategies/constants.py`**: Single source for ORDER_SUN, ORDER_HOKUM, PTS_SUN, PTS_HOKUM, SUITS, RANKS
- [ ] 8.1b **Refactor all 12+ files**: Replace local constant definitions with `from ai_worker.strategies.constants import ...`
- [ ] 8.1c **Add divergence test**: Write test that imports from both `game_engine/models/constants.py` and `ai_worker/strategies/constants.py`, asserts they match
- [ ] 8.1d **Update CLAUDE.md**: Change the "no cross-imports between strategy components" rule to allow importing from the shared constants module

> **Note**: This changes the architectural rule about module independence. The tradeoff is worth it: 12 files with duplicated constants is a real divergence risk, and importing constants (not logic) from a shared module doesn't create coupling between strategy modules.

### 8.2 Type Safety Improvements
- [ ] 8.2a **Add `GameMode` type alias**: Replace all `mode: str` with `Literal["SUN", "HOKUM"]` in strategy function signatures
- [ ] 8.2b **Add `Position` type alias**: Replace `str` with `Literal["Bottom", "Right", "Top", "Left"]`
- [ ] 8.2c **Add `Suit` type alias**: Replace `str` with `Literal["♠", "♥", "♦", "♣"]`
- [ ] 8.2d **Run mypy**: Fix any type errors surfaced by the new types

### 8.3 Dead Code Removal
- [ ] 8.3a **Audit all strategy modules**: Find and remove any remaining dead code (unreachable branches, unused variables, commented-out blocks)
- [ ] 8.3b **Remove deprecated DisputeModal**: Frontend has modern Qayd system; legacy fallback is dead weight
- [ ] 8.3c **Clean up debug print/log statements**: Replace any `print()` calls with proper `logger.debug()`

---

## Mission 9: Production Hardening (Est: 10-14 hours)
Priority: MEDIUM — Required for deployment

### 9.1 Security Fixes
- [ ] 9.1a **JWT secret from env**: Replace hardcoded JWT secret with `os.environ["JWT_SECRET"]`, fail fast if missing
- [ ] 9.1b **CORS whitelist**: Replace `allow_origins=["*"]` with specific frontend origin(s) from env var
- [ ] 9.1c **WebSocket input validation**: Add Pydantic schema validation for all incoming socket messages (bid, play_card, etc.)
- [ ] 9.1d **Rate limiting**: Add per-connection rate limit for socket messages (prevent spam/DOS)
- [ ] 9.1e **Sanitize player names**: Prevent XSS via player name injection in chat/emotes

### 9.2 Containerization
- [ ] 9.2a **Backend Dockerfile**: Python 3.11, install deps, run FastAPI with uvicorn
- [ ] 9.2b **Frontend Dockerfile**: Node 20, build Vite, serve with nginx
- [ ] 9.2c **Docker Compose**: Redis + Backend + Frontend + Celery worker, health checks, restart policies
- [ ] 9.2d **Environment config**: `.env.example` with all required variables documented

### 9.3 CI/CD Pipeline
- [ ] 9.3a **GitHub Actions — Test**: Run `pytest tests/bot/ tests/game_logic/` on push/PR
- [ ] 9.3b **GitHub Actions — Lint**: Run `ruff check` (or flake8) on Python code
- [ ] 9.3c **GitHub Actions — Frontend**: Run `npm run build` to catch TypeScript errors
- [ ] 9.3d **GitHub Actions — Docker**: Build images on merge to main, push to registry

### 9.4 Database & Persistence
- [ ] 9.4a **Alembic setup**: Initialize migration system for SQLite/Postgres
- [ ] 9.4b **Schema migration**: Version the current schema, add `alembic upgrade head` to startup
- [ ] 9.4c **Redis connection resilience**: Add retry logic and graceful fallback if Redis is down
- [ ] 9.4d **Match archival**: Ensure archived matches are stored in DB, not just Redis (data durability)

---

## Mission 10: Competitive Edge — Advanced AI (Est: 16-20 hours)
Priority: LOW — Polish and tournament-grade AI

### 10.1 Suit Combination Tables
- [ ] 10.1a **Build probability engine**: Given known cards and void info, calculate exact probability of winning a lead in each suit
- [ ] 10.1b **Wire into lead_selector**: Replace heuristic "master card" check with probability-based suit ranking
- [ ] 10.1c **Cache calculations**: Memoize per trick (hand changes each trick, but within a decision, probabilities are fixed)

### 10.2 Safety Play Engine
- [ ] 10.2a **Safety play module**: When our team has enough GP to win, switch to "lose minimum" mode — don't risk tricks for extra points
- [ ] 10.2b **Maximum play module**: When behind, calculate the play that maximizes expected GP (even if risky)
- [ ] 10.2c **Integrate with score_context**: Auto-select safety vs maximum based on match state

### 10.3 Endplay & Squeeze Detection
- [ ] 10.3a **Throw-in endplay**: Detect when giving lead to opponent forces them to lead into our strong suit
- [ ] 10.3b **Trump squeeze**: Detect when cashing trump forces opponent to discard a winner
- [ ] 10.3c **Wire into endgame_solver**: These become preferred plays in the minimax tree

### 10.4 Bot Personalities
- [ ] 10.4a **Personality system**: Define 4 profiles: Aggressive (lower thresholds, more doubles), Conservative (higher thresholds, safe plays), Tricky (bluffs, unexpected leads), Balanced (default)
- [ ] 10.4b **Apply to bidding**: Aggressive bids on borderline hands, Conservative passes
- [ ] 10.4c **Apply to playing**: Tricky leads unexpected suits, Conservative avoids risky plays
- [ ] 10.4d **UI selector**: Let player choose opponent difficulty/style before match

### 10.5 Self-Play Training Loop
- [ ] 10.5a **Self-play harness**: 4 bots play 1000 matches, record all decisions + outcomes
- [ ] 10.5b **Threshold optimizer**: Analyze which confidence thresholds correlate with winning → auto-tune
- [ ] 10.5c **Strategy weight optimizer**: Adjust brain cascade priorities based on win rate per module
- [ ] 10.5d **ELO system**: Rate bots by configuration, match weaker players against easier configs

### 10.6 Baloot-Specific Exploits
- [ ] 10.6a **Ekl trap**: In HOKUM, if you must beat trump, play the minimum winning trump (save J/9 for later)
- [ ] 10.6b **Ashkal bluff detection**: If opponent plays Ashkal but their early cards suggest weak SUN hand, adjust defense
- [ ] 10.6c **Kawesh timing**: Request Kawesh strategically when opponent team is close to winning (forces redeal, wastes their momentum)

---

## Mission 11: Backend Correctness & Safety (Est: 8-10 hours)
Priority: HIGH — Scoring bugs and race conditions affect gameplay integrity

### 11.1 Scoring Engine Fixes ✅
Verified and locked in `game_engine/logic/scoring_engine.py`:
- [x] 11.1a **GP tiebreak overflow**: Already fixed — subtracts diff from non-bidder when `total_gp > target_total` (lines 95-101)
- [x] 11.1b **HOKUM rounding rule locked**: `.5` rounds DOWN, `.6+` rounds UP (`> 0.5` check). Tests added to lock this behavior
- [x] 11.1c **Empty round_history guard**: Already fixed — early return at line 37-38
- [x] 11.1d **Test scoring edge cases**: 9 tests added covering GP overflow, HOKUM rounding, SUN rounding, empty/None history

### 11.2 Server Handler Input Validation ✅
`server/handlers/game_actions.py` — comprehensive validation added:
- [x] 11.2a **Action type validation**: Already validates `action in VALID_ACTIONS` set (line 42)
- [x] 11.2b **BID payload validation**: Added type checks for `bid_action` (must be str) and `bid_suit` (must be in ♠♥♦♣)
- [x] 11.2c **roomId validation**: Already validates string type, non-empty, max 64 chars (line 40)
- [x] 11.2d **Settings validation**: Added range check for turnDuration (1-120s), type-safe conversion

### 11.3 Race Condition Fixes ✅
- [x] 11.3a **Auto-restart lock**: `is_restarting` flag with try/finally cleanup already in game_lifecycle.py (line 110-198)
- [x] 11.3b **Bot loop depth safety**: Already has `recursion_depth > 500` guard (line 143). In-process single-threaded with eventlet — atomic enough
- [x] 11.3c **Redis SCAN**: Replaced `redis_store.keys("game:*")` with cursor-based `redis_store.scan()` in both `clear_all_games()` and `games` property to avoid blocking Redis
- [x] 11.3d **Sawa timer cleanup**: Already verifies game exists and sawa still pending after sleep (lines 79-86)

### 11.4 Error Handling Improvements ✅
- [x] 11.4a **room_manager.get_game**: Already uses narrower catches (JSONDecodeError, KeyError, TypeError) + ConnectionError + fallback Exception (lines 71-76)
- [x] 11.4b **room_manager.save_game**: Already updates cache only after Redis write (line 99, moved in M14)
- [x] 11.4c **Bot agent narrower except**: Split catch-all into expected errors (KeyError/IndexError/AttributeError/TypeError/ValueError) at ERROR level + unexpected at CRITICAL level
- [x] 11.4d **BotContext empty hand guard**: Added early return `[]` with error log when `self.hand` is empty in `get_legal_moves()`

### 11.5 Bidding Engine Robustness ✅
- [x] 11.5a **from_dict player validation**: Already validates `len(players) != 4` raises ValueError (line 97-98)
- [x] 11.5b **Phase-contract consistency**: process_bid already checks phase at line 182 (FINISHED guard) + delegates to correct handler per phase
- [x] 11.5c **Kawesh hand type safety**: `is_kawesh_hand()` now handles Card objects, dicts, empty/None hands via `getattr()` + isinstance checks. 6 tests added

---

## Mission 12: Frontend Stability & Performance (Est: 10-12 hours)
Priority: HIGH — Memory leaks and race conditions cause crashes in long sessions

### 12.1 Hook Memory Leak Fixes
Multiple hooks register event listeners or timers without proper cleanup:
- [ ] 12.1a **useGameSocket cleanup**: Store cleanup functions in refs, always call them in useEffect cleanup even when roomId is null. Currently early-return on `!roomId` skips cleanup registration
- [ ] 12.1b **useBiddingLogic timeout cleanup**: `setTimeout` for `startNewRound` (line ~48) has no cleanup. Store timeout ID in ref, clear on unmount
- [ ] 12.1c **useRoundManager unmount safety**: `setTimeout` for `startNewRound` (line ~179) can fire after unmount. Track mounted state with ref, cancel timer in cleanup
- [ ] 12.1d **useEmotes flying item cleanup**: `setTimeout` to remove flying items has no cleanup. Store timeout IDs, clear all on unmount
- [ ] 12.1e **usePlayingLogic turn timer**: Timer doesn't check if turn has changed before firing. Store timer ref, clear on turn change

### 12.2 Stale Closure & Dependency Fixes
- [ ] 12.2a **useGameSocket sendAction**: `isSendingAction` captured in closure may be stale. Replace state check with `isSendingRef.current` (ref-based check avoids re-creating callback)
- [ ] 12.2b **useLocalBot over-triggering**: Effect depends on entire `gameState` object, causing heartbeat to restart on every state change. Destructure to `[gameState.phase, gameState.currentTurnIndex]` only
- [ ] 12.2c **useGameSocket rotation race**: `myIndexRef.current` may be stale when rapid updates arrive. Use functional setState pattern: `setState(prev => rotateGameState(serverState, prev.myIndex))`
- [ ] 12.2d **useBotSpeech overlap**: Multiple rapid messages create overlapping timeouts. Use unique message IDs and track active timeouts per player in refs

### 12.3 Performance Optimizations
- [ ] 12.3a **Memoize Table/ClassicBoard**: Wrap in `React.memo` with custom comparison — only re-render when `phase`, `tableCards`, `currentTurnIndex`, or `players[].hand` change
- [ ] 12.3b **Consolidate toast logic**: Toast detection is duplicated in Table.tsx, ClassicBoard.tsx, and useGameAudio. Extract to single `useToastDetector` hook
- [ ] 12.3c **Debounce localStorage writes**: `useShop` writes to localStorage on every state change. Add 500ms debounce
- [ ] 12.3d **useMemo for card validity**: Legal move calculation in `usePlayingLogic` should be memoized — currently recalculates on every render

### 12.4 Error Boundaries & Resilience
- [ ] 12.4a **Wrap all modals in ErrorBoundary**: Currently only 2 FeatureErrorBoundary instances. Add boundaries around RoundResultsModal, SettingsModal, VictoryModal, StoreModal, SawaModal, etc.
- [ ] 12.4b **Socket reconnection state restore**: `SocketService` reconnects but doesn't re-join room or restore state. After reconnect, emit `rejoin_room` with stored roomId
- [ ] 12.4c **Add global error state**: When socket disconnects, show banner "Connection lost — reconnecting..." instead of silent failure
- [ ] 12.4d **Null guard in trickUtils**: `isValidMove` doesn't validate card is not null/undefined. Add guard clause at function start

---

## Mission 13: Frontend-Backend Contract Alignment (Est: 6-8 hours)
Priority: MEDIUM — Mismatches between frontend expectations and backend responses

### 13.1 Type Safety
- [ ] 13.1a **Eliminate `any` types**: Replace `metadata?: any` in types.ts with proper `CardMetadata` interface. Replace `fullMatchHistory?: any[]` with `MatchRound[]`. Remove `[key: string]: any` index signature
- [ ] 13.1b **Enforce PlayerPosition enum**: Some places use string literals ("Bottom"), others use `PlayerPosition.Bottom` enum. Standardize on enum everywhere
- [ ] 13.1c **Add Baloot state types**: Frontend `types.ts` needs `BalootState` interface matching backend `baloot_manager.get_state()` output
- [ ] 13.1d **Add Qayd state types**: Ensure `QaydState` interface matches backend `qayd_engine.state` structure exactly

### 13.2 Config & Environment
- [ ] 13.2a **Fix production URL**: `config.ts` line 3 returns `localhost:3005` for BOTH dev and production. Use `import.meta.env.VITE_API_URL` with fallback to localhost
- [ ] 13.2b **Add env validation**: On app startup, validate required env vars exist (`VITE_API_URL`, etc.) and log warnings for missing ones
- [ ] 13.2c **Centralize game constants**: `RANKS_ORDER`, `POINT_VALUES`, `STRENGTH_ORDER` are duplicated across frontend files. Create single `gameConstants.ts` matching backend `constants.py`

### 13.3 Frontend Feature Gaps
- [ ] 13.3a **Baloot announcement UI**: Backend emits BALOOT_ANNOUNCED and BALOOT_DECLARED events but frontend has no visual indicator. Add toast/animation when Baloot is announced, celebration when declared
- [ ] 13.3b **Baloot score display**: RoundResultsModal should show Baloot 2 GP as separate line item (immune to doubling), not lumped into trick points
- [ ] 13.3c **Galoss visual indicator**: When galoss_guard triggers emergency mode, show a subtle warning indicator on the bot's avatar (e.g., red glow = desperate, green glow = pressing advantage)
- [ ] 13.3d **Project hierarchy display**: When a 100-project blocks a smaller project, show the blocking relationship in the project reveal animation

### 13.4 Accessibility Basics
- [ ] 13.4a **Card aria-labels**: All cards need `aria-label="Ace of Spades"` (or Arabic equivalent) for screen readers
- [ ] 13.4b **Keyboard card selection**: Allow tab/arrow keys to navigate hand, Enter to play selected card
- [ ] 13.4c **Bid button aria-labels**: Bid buttons need descriptive labels ("Bid Hokum Spades", "Pass this round")
- [ ] 13.4d **Color contrast**: Ensure all text meets WCAG AA contrast ratio (4.5:1 minimum)

---

## Mission 14: Server Security & Deployment (Est: 8-10 hours)
Priority: MEDIUM — Required before any public access

### 14.1 Authentication & Authorization
- [ ] 14.1a **CORS lock**: `socket_handler.py` line 18 has `cors_allowed_origins='*'`. Replace with env-based whitelist: `os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')`
- [ ] 14.1b **JWT enforcement**: Add Socket.IO connect middleware that verifies JWT token for ALL connections. Reject unauthenticated connections
- [ ] 14.1c **Strong JWT secret**: `auth_utils.py` falls back to `'dev-secret-key-change-in-prod'`. In production, require `JWT_SECRET` env var and fail fast if missing or still default
- [ ] 14.1d **Player ownership check**: In `game_actions.py`, verify that the acting player matches the current turn (prevent impersonation by spoofed SID)

### 14.2 Input Sanitization
- [ ] 14.2a **Player name sanitization**: Strip HTML tags and limit to 20 characters to prevent XSS injection via player names displayed in UI
- [ ] 14.2b **Room ID validation**: Enforce UUID format for room IDs to prevent path traversal or injection via crafted IDs
- [ ] 14.2c **Rate limit tightening**: Current 20 actions/second is too high. Reduce to 5/second for game_action, keep higher for read-only events
- [ ] 14.2d **Payload size limit**: Add max payload size (e.g., 4KB) to reject oversized messages

### 14.3 Operational Resilience
- [ ] 14.3a **Redis SCAN instead of KEYS**: `room_manager.py` uses `redis_store.keys("game:*")` which blocks Redis. Replace with cursor-based `SCAN`
- [ ] 14.3b **Log rotation**: `timer_monitor.log` and `client_debug.log` append forever. Switch to `RotatingFileHandler` with 10MB max, 5 backups
- [ ] 14.3c **Rate limiter fail-closed**: `rate_limiter.py` returns `True` (allow) when Redis is down. Change to fail-closed (deny) for security-critical endpoints
- [ ] 14.3d **Archiver error alerting**: `archiver.py` swallows all exceptions silently. Add structured error logging with match ID for debugging

### 14.4 Containerization & CI
- [ ] 14.4a **Backend Dockerfile**: Python 3.11-slim, non-root user, multi-stage build, health check endpoint
- [ ] 14.4b **Frontend Dockerfile**: Node 20 build stage → nginx serve stage, gzip enabled
- [ ] 14.4c **Docker Compose**: Redis + Backend + Frontend + Celery worker, named volumes for Redis persistence, restart=unless-stopped
- [ ] 14.4d **GitHub Actions CI**: Test (pytest) → Lint (ruff) → Build (docker) on push/PR, deploy on merge to main

---

## Mission 16: "The Mind" — Bot Personality & Difficulty System (Est: 8-10 hours)
Priority: HIGH — Players need varied, engaging opponents

### 16.1 Personality Profiles
Define 4 distinct bot personalities that affect both bidding and playing style:
- [ ] 16.1a **Create `ai_worker/strategies/personality.py`**: Pure function `apply_personality(base_decision, profile, context) -> modified_decision` that adjusts confidence thresholds, aggression, and risk tolerance
- [ ] 16.1b **"Aggressive" profile** (لعّيب): Lower bid thresholds by 15%, always double when borderline, prefer trump leads, chase Kaboot when 5+ tricks, confidence +0.1 on attack plays
- [ ] 16.1c **"Conservative" profile** (حذر): Raise bid thresholds by 20%, never double unless certain, protect point cards, prefer safe leads, confidence +0.1 on defense plays
- [ ] 16.1d **"Tricky" profile** (مخادع): Bluff with unexpected leads 30% of the time, false signal in partner suits, underplay strong hands early then dominate late, randomize between top-2 recommendations
- [ ] 16.1e **"Balanced" profile** (متوازن): Current default behavior, no modifications — serves as baseline

### 16.2 Difficulty Levels
- [ ] 16.2a **Create `ai_worker/strategies/difficulty.py`**: Pure function `apply_difficulty(recommendations, level) -> filtered_recommendations` that degrades bot play quality at lower levels
- [ ] 16.2b **Easy mode**: Bot "forgets" card counting 40% of the time (ignores tracker voids), makes random play 15% of the time, never pursues Kaboot, uses only top-3 brain cascade steps
- [ ] 16.2c **Medium mode**: Occasional suboptimal plays (10% chance of picking 2nd-best card), no endgame solver, reduced Bayesian accuracy (add noise to probabilities)
- [ ] 16.2d **Hard mode**: Full AI strength, all modules active, endgame solver enabled, optimal Kaboot pursuit
- [ ] 16.2e **"Khalid" mode** (خالد): Expert+ — aggressive Kaboot pursuit even at risk, perfect memory, maximum trump efficiency, deliberate Galoss pressure on opponents

### 16.3 Wiring & UI
- [ ] 16.3a **Wire into sun.py/hokum.py**: Apply personality + difficulty before returning final decision
- [ ] 16.3b **Wire into bidding.py**: Apply personality to bid thresholds, difficulty to bid evaluation quality
- [ ] 16.3c **Frontend difficulty selector**: Pre-game screen with 4 difficulty buttons + personality preview (name + Arabic subtitle + 1-line description)
- [ ] 16.3d **Bot avatar differentiation**: Each personality gets a distinct avatar style/color (e.g., Aggressive=red border, Conservative=blue, Tricky=purple, Balanced=green)
- [ ] 16.3e **Test**: Play 100 games per difficulty → Easy should lose ~70%, Medium ~50%, Hard ~30%, Khalid ~15%

---

## Mission 17: "The Teacher" — Interactive Tutorial & Learning Mode (Est: 10-12 hours)
Priority: HIGH — Critical for player onboarding and retention

### 17.1 Guided Tutorial
Step-by-step first-game experience that teaches Baloot rules:
- [ ] 17.1a **Create `frontend/src/components/Tutorial.tsx`**: Full-screen overlay tutorial system with step progression, highlighting, and tooltips
- [ ] 17.1b **Lesson 1 — Card Basics**: Show all 32 cards, explain SUN vs HOKUM rank orders, point values. Interactive: "Which card is worth more? Tap to answer"
- [ ] 17.1c **Lesson 2 — Bidding**: Walk through a sample bidding round. Explain Pass/Hokum/Sun/Ashkal. Interactive: "You have this hand, what would you bid?"
- [ ] 17.1d **Lesson 3 — Trick Play**: Play 3 tricks with guided hand (highlight which cards are legal, explain why). Show trick winner logic
- [ ] 17.1e **Lesson 4 — Scoring**: Explain Abnat, GP, Khasara, Kaboot. Show a sample round result breakdown
- [ ] 17.1f **Lesson 5 — Projects**: Explain Sira, 50, 100, 400. Show project hierarchy and blocking rules
- [ ] 17.1g **Lesson 6 — Special Rules**: Baloot declaration, Kawesh, Ashkal, Doubling, Sawa, Galoss

### 17.2 Learning Mode (Hint System)
- [ ] 17.2a **Create `frontend/src/hooks/useHintSystem.ts`**: Hook that provides play hints when enabled
- [ ] 17.2b **Backend hint API**: New socket event `request_hint` → runs bot AI on player's hand → returns top-3 recommendations with explanations
- [ ] 17.2c **Bid hints**: "Your hand is strong in ♠ (J+9+A). Consider bidding Hokum ♠" with confidence meter
- [ ] 17.2d **Play hints**: "Lead your A♠ — it's a master card and likely to win this trick" with card glow effect
- [ ] 17.2e **Post-trick analysis**: "You played 7♥ but Q♥ would have won the trick (partner was already winning)" — shows after each trick if enabled
- [ ] 17.2f **Toggle**: Settings > "Show Hints" toggle, default OFF, with "Beginner Mode" that auto-enables hints + slower bot play

### 17.3 Practice Mode
- [ ] 17.3a **Scenario builder**: Predefined deal setups for common Baloot situations (strong trump hand, defensive hand, Kaboot opportunity, Galoss danger)
- [ ] 17.3b **Undo/redo**: Allow taking back the last play to try different strategies
- [ ] 17.3c **Card reveal**: Option to see all 4 hands (for learning optimal play)
- [ ] 17.3d **Speed controls**: Pause after each trick, slow bot play (3s delay vs 1s), fast-forward

---

## Mission 18: "The Showman" — Game Feel & Polish (Est: 8-10 hours)
Priority: HIGH — Makes the game feel alive and premium

### 18.1 Card Animations
- [ ] 18.1a **Create `frontend/src/hooks/useCardAnimation.ts`**: Animation orchestrator using CSS transitions + requestAnimationFrame
- [ ] 18.1b **Deal animation**: Cards fly from deck position to each player's hand in sequence (0.15s per card, staggered)
- [ ] 18.1c **Play animation**: Card slides from hand → table center with slight rotation (0.3s ease-out)
- [ ] 18.1d **Trick-win sweep**: All 4 table cards slide toward winner's avatar, scale down, fade (0.5s)
- [ ] 18.1e **Trump card glow**: Trump suit cards have a subtle golden border shimmer when in hand
- [ ] 18.1f **Kaboot celebration**: When a team wins all 8 tricks — screen-wide confetti + cards cascade + "كبوت!" text explosion

### 18.2 Sound Design
The SoundManager already exists with basic synthesis. Expand it:
- [ ] 18.2a **Card sounds**: Different tones for play-card, win-trick, lose-trick (use existing playCardSound/playWinSound/playLoseSound but refine oscillator frequencies)
- [ ] 18.2b **Bid sounds**: Distinct sounds for Pass (soft thud), Hokum (confident chime), Sun (bright fanfare), Double (dramatic drum)
- [ ] 18.2c **Tension sounds**: Use existing useGameTension hook — at `high` tension play subtle ambient drone, at `critical` add heartbeat bass
- [ ] 18.2d **Victory/defeat jingle**: 2-3 second musical stinger for match win/loss
- [ ] 18.2e **Kaboot sound**: Dramatic boom + triumphant brass (synthesized)
- [ ] 18.2f **Volume controls**: Per-category sliders in SettingsModal (Music, SFX, Ambient)

### 18.3 Visual Polish
- [ ] 18.3a **Table felt texture**: CSS gradient background that looks like green felt cloth (replace flat color)
- [ ] 18.3b **Card shadows**: Dynamic drop shadows that change based on card state (in-hand: soft, played: sharp, highlighted: glow)
- [ ] 18.3c **Turn indicator**: Pulsing golden ring around current player's avatar (replace static highlight)
- [ ] 18.3d **Score animation**: Numbers count up/down with easing in ScoreSheet when points change
- [ ] 18.3e **Bid indicator chips**: Show current bid as a poker-style chip on the table (Hokum ♠, Sun, Dobl, etc.)
- [ ] 18.3f **Dark/light theme**: Full theme toggle (dark table + light cards vs light table + dark accents)

### 18.4 Mobile Experience
- [ ] 18.4a **Responsive card fan**: Cards scale and overlap dynamically at screen widths < 480px
- [ ] 18.4b **Touch gestures**: Swipe card upward to play, long-press to preview, pinch to zoom table
- [ ] 18.4c **Bottom-sheet modals**: Convert modals to bottom sheets on mobile (swipe down to dismiss)
- [ ] 18.4d **Portrait optimization**: Rearrange table layout for portrait mode (current player bottom, partner top)

---

## Mission 19: "The Historian" — Match Replay & Statistics (Est: 6-8 hours)
Priority: MEDIUM — Player engagement and learning from past games

### 19.1 Full Match Replay
The replay hook exists (useReplayNavigation) but only shows trick-by-trick summaries. Make it visual:
- [ ] 19.1a **Visual replay**: Render the actual table with cards being played in sequence (reuse Table component with replay data)
- [ ] 19.1b **Playback controls**: Play/Pause, Speed (0.5x, 1x, 2x, 4x), Skip trick, Skip round, Jump to trick N
- [ ] 19.1c **Timeline scrubber**: Horizontal bar showing all tricks in all rounds, with markers for key events (Kaboot, Baloot, Khasara, Double)
- [ ] 19.1d **Commentary track**: Auto-generated analysis per trick ("Team A won with A♠, collecting 21 Abnat", "Player 3 signaled void in ♦")
- [ ] 19.1e **AI analysis overlay**: Toggle to show what the bot would have played vs what the human played, with confidence scores

### 19.2 Player Statistics
- [ ] 19.2a **Create `frontend/src/services/StatsTracker.ts`**: Persist match results to localStorage, compute aggregates
- [ ] 19.2b **Dashboard screen**: Win/Loss record, win rate %, average GP per round, Kaboot count, Galoss count, favorite bid, longest win streak
- [ ] 19.2c **Per-difficulty stats**: Separate stats for Easy/Medium/Hard/Khalid games
- [ ] 19.2d **Achievements**: Unlock badges for milestones (First Win, 10-Win Streak, Kaboot Master, Sun King, Hokum Hero, Galoss Survivor, etc.)
- [ ] 19.2e **Session history**: Scrollable list of last 50 matches with result, opponent difficulty, notable events

### 19.3 Match Export
- [ ] 19.3a **Export to JSON**: Download full match data (all tricks, all bids, all cards) for analysis
- [ ] 19.3b **Share replay link**: Generate a URL that encodes the match seed + all decisions (deterministic replay)
- [ ] 19.3c **Screenshot mode**: Capture current table state as shareable image with team scores overlay

---

## Mission 20: "The Arena" — Multiplayer & Social Features (Est: 12-16 hours)
Priority: MEDIUM — Core value proposition for online play

### 20.1 Room System Enhancement
- [ ] 20.1a **Room browser**: Lobby screen showing available rooms with player count, game status (Waiting/In Progress), and difficulty setting
- [ ] 20.1b **Private rooms**: Room codes (4-6 character alphanumeric) that players share to join. Host sets rules (difficulty, timer length, match target)
- [ ] 20.1c **Quick match**: One-click matchmaking — auto-join or create a room with default settings, fill empty seats with bots
- [ ] 20.1d **Reconnection**: If a player disconnects mid-game, hold their seat for 60s. Bot takes over temporarily. On reconnect, restore full state and return control
- [ ] 20.1e **Spectator mode**: Join a room as observer — see all cards (or only played cards), no actions allowed, chat-only

### 20.2 In-Game Communication
The EmoteMenu already exists. Expand the social layer:
- [ ] 20.2a **Quick chat phrases**: Predefined Arabic/English Baloot phrases: "يا سلام!" (Great play!), "كمل كمل" (Keep going), "صبر" (Patience), "خلاص" (That's it), "ما عندي" (I have nothing)
- [ ] 20.2b **Team-only chat**: Private message to partner only (opponent can't see). Useful for real signaling beyond card play
- [ ] 20.2c **Emote reactions**: React to a specific trick or bid with floating emoji (thumbs up, facepalm, fire, etc.)
- [ ] 20.2d **Mute/block**: Mute individual player's emotes and chat. Block persists across sessions (localStorage)

### 20.3 Player Profiles
- [ ] 20.3a **Profile screen**: Display name (editable), avatar selection (8-12 preset avatars), level, total wins
- [ ] 20.3b **XP system**: Gain XP for playing matches (+10 win, +3 loss, +5 Kaboot bonus, +2 per Baloot). Level up thresholds: 0, 50, 150, 300, 500, 800, 1200...
- [ ] 20.3c **Level badges**: Show player level next to name in lobby and in-game (Level 1-5: Bronze, 6-10: Silver, 11-20: Gold, 21+: Diamond)
- [ ] 20.3d **Leaderboard**: Top 20 players by win rate (minimum 10 games), total wins, and Kaboot count

---

## Mission 21: "The Brain Surgeon" — Advanced AI Intelligence (Est: 10-14 hours)
Priority: MEDIUM — Tournament-grade bot play

### 21.1 Probabilistic Memory Upgrade
The current CardMemory uses binary void tracking. Upgrade to Bayesian distributions:
- [ ] 21.1a **Implement "Mind's Eye"** (TODO in memory.py line 52): Replace binary void tracking with probability distributions `{player: {suit: float}}` where float = probability of holding cards in that suit
- [ ] 21.1b **Update on each trick**: When a player follows suit → increase their probability. When they discard → decrease toward 0. When they trump → set suit probability to 0 and increase trump probability
- [ ] 21.1c **Prior estimation**: Use bid information as Bayesian priors (bid Hokum ♠ → P(strong ♠) = 0.85). Use hand shape distributions as secondary prior
- [ ] 21.1d **Wire into all consumers**: Update lead_selector, follow_optimizer, trump_manager, defense_plan to use probabilistic queries instead of binary void checks

### 21.2 Score-Aware Play Engine
- [ ] 21.2a **Create `ai_worker/strategies/components/score_context.py`**: `get_score_context(team_scores, match_scores) -> {phase, aggression_mod, risk_tolerance}`
- [ ] 21.2b **Match phases**: EARLY (0-50 GP), MID (50-100), LATE (100-145), MATCH_POINT (145+). Each phase shifts risk tolerance
- [ ] 21.2c **Safety play**: When ahead in a round by 10+ GP and 5+ tricks, switch to "protect the lead" mode — play low, avoid risks, let opponents waste high cards
- [ ] 21.2d **Desperation play**: When behind by 100+ match points, lower all bid thresholds by 25%, pursue Kaboot even at 30% chance, always double when ahead in round
- [ ] 21.2e **Match point discipline**: At 145+ match points, become ultra-conservative — never risk Khasara, prefer safe bids even if slightly suboptimal

### 21.3 Endplay & Squeeze Detection
- [ ] 21.3a **Throw-in detection**: At 2-3 cards remaining, detect when giving lead forces opponent to lead into our strong suit. Execute throw-in play
- [ ] 21.3b **Trump squeeze**: When cashing last trumps, detect if opponent must discard a side-suit winner. Time trump plays to maximize squeeze pressure
- [ ] 21.3c **Wire into endgame_solver**: Add throw-in and squeeze as preferred nodes in minimax tree (bonus score for executing)
- [ ] 21.3d **Test**: Create 10 handcrafted endgame positions, verify bot finds the endplay/squeeze when it exists

### 21.4 Self-Play Evaluation Harness
- [ ] 21.4a **Create `scripts/self_play.py`**: Run N matches between 4 bots, record every decision + outcome
- [ ] 21.4b **ELO rating**: After each match, update bot ELO ratings based on win/loss. Start all bots at 1500
- [ ] 21.4c **A/B testing**: Compare two bot configurations (e.g., with vs without opponent_model) over 500 games. Report win rate difference with statistical significance
- [ ] 21.4d **Threshold tuner**: Binary search for optimal confidence threshold in brain.py cascade — run 100 games per threshold value, find the sweet spot
- [ ] 21.4e **Dashboard output**: Generate HTML report with: win rates, ELO progression, average GP, Kaboot frequency, decision distribution charts

---

## Mission 22: "The Stage" — Production-Ready Game Experience (Est: 10-12 hours)
Priority: LOW — Final polish before public release

### 22.1 Localization
- [ ] 22.1a **Arabic-first UI**: All game text in Arabic by default (بلوت, صن, حكم, مشروع, etc.). Use Arabic number formatting
- [ ] 22.1b **Create `frontend/src/i18n/`**: Translation system with `ar.json` and `en.json` files. Use React context for language switching
- [ ] 22.1c **RTL layout**: Ensure all UI components work correctly in RTL mode (card fan direction, score sheet, modals)
- [ ] 22.1d **Language toggle**: In SettingsModal, add Arabic/English switch that persists to localStorage

### 22.2 Performance & Loading
- [ ] 22.2a **Code splitting**: Lazy-load MatchReviewModal, SettingsModal, StoreModal, Tutorial (they're heavy and not needed immediately)
- [ ] 22.2b **Asset preloading**: Preload card images and sound effects during splash screen
- [ ] 22.2c **Skeleton loading**: Show card-shaped skeleton placeholders while game state loads
- [ ] 22.2d **Bundle analysis**: Run Vite bundle analyzer, identify and eliminate dead imports, target < 200KB gzipped

### 22.3 PWA & Offline Support
- [ ] 22.3a **Service worker**: Cache static assets for offline single-player mode
- [ ] 22.3b **Install prompt**: "Add to Home Screen" prompt on mobile browsers
- [ ] 22.3c **Offline indicator**: Show "Offline Mode — Playing against bots" banner when no network
- [ ] 22.3d **Manifest**: App icon, theme color, display: standalone for native-app feel

### 22.4 Containerization & Deployment
- [ ] 22.4a **Backend Dockerfile**: Python 3.11-slim, multi-stage build, non-root user, health check endpoint
- [ ] 22.4b **Frontend Dockerfile**: Node 20 build → nginx serve, gzip enabled, SPA fallback
- [ ] 22.4c **Docker Compose**: Full stack: Redis + Backend + Frontend + optional Celery worker. Named volumes, restart policies, health checks
- [ ] 22.4d **GitHub Actions CI**: Test → Lint → Build → Deploy pipeline. Auto-run on push/PR
- [ ] 22.4e **`.env.example`**: Document all required environment variables with defaults and descriptions

---

## Progress Summary

| Mission | Status | Tests Before | Tests After |
|---------|--------|-------------|-------------|
| 1. Bug Fixes | ✅ Complete | 370 | 403 |
| 2. Wire Brain | ✅ Complete | 403 | 403 |
| 3. Bidding | ✅ Complete | 403 | 403 |
| 4. Playing Depth | ✅ Complete | 403 | 329* |
| 5. Engine Complete | ✅ Complete | 329 | 329 |
| 6. Test Fortress | ⬜ Pending | 329 | — |
| 7. Brain Expansion | ⬜ Pending | — | — |
| 8. Architecture | ⬜ Pending | — | — |
| 9. Production | ⬜ Pending | — | — |
| 10. Advanced AI | ⬜ Pending | — | — |
| 11. Backend Safety | ✅ Complete | 332 | 353 |
| 12. Frontend Stability | ⬜ Pending | — | — |
| 13. FE-BE Alignment | ⬜ Pending | — | — |
| 14. Server Security | ⬜ Pending | — | — |
| 15. Constants + Brain | ✅ Complete | 332 | 332 |
| **16. Bot Personality** | ⬜ Pending | — | — |
| **17. Tutorial & Hints** | ⬜ Pending | — | — |
| **18. Game Feel** | ⬜ Pending | — | — |
| **19. Replay & Stats** | ⬜ Pending | — | — |
| **20. Multiplayer** | ⬜ Pending | — | — |
| **21. Advanced AI** | ⬜ Pending | — | — |
| **22. Production Ready** | ⬜ Pending | — | — |

*Test count decreased because test infrastructure was reorganized; no tests were lost, some were consolidated.

---

**Missions 1-5 (Critical Path): ✅ COMPLETE**
**Mission 15 (Constants + Brain Wiring): ✅ COMPLETE**
**Missions 6-14 (Existing Pending): ⬜ ~80-102 hours across 9 missions**
**Missions 16-22 (Game Improvement): ⬜ ~65-82 hours across 7 missions**
**Total Remaining: ~145-184 hours across 16 missions**

### Recommended Execution Order

**Phase 1 — Fix & Stabilize**
1. **Mission 11** (Backend Safety) — Fix scoring bugs + race conditions
2. **Mission 6** (Test Fortress) — Lock correctness with tests
3. **Mission 12** (Frontend Stability) — Fix memory leaks + crashes

**Phase 2 — Make It Fun**
4. **Mission 16** (Bot Personality) — Varied, engaging opponents
5. **Mission 18** (Game Feel) — Animations, sounds, polish
6. **Mission 17** (Tutorial) — Player onboarding

**Phase 3 — Make It Smart**
7. **Mission 7** (Brain Expansion) — Wire remaining AI modules
8. **Mission 21** (Advanced AI) — Probabilistic memory, endplays, self-play
9. **Mission 8** (Architecture) — Clean up technical debt

**Phase 4 — Make It Social**
10. **Mission 19** (Replay & Stats) — Match history, achievements
11. **Mission 20** (Multiplayer) — Rooms, matchmaking, social
12. **Mission 13** (FE-BE Alignment) — Wire backend to frontend

**Phase 5 — Ship It**
13. **Mission 14** (Server Security) — Lock down for deployment
14. **Mission 9** (Production) — Containerize and CI/CD
15. **Mission 22** (Production Ready) — Localization, PWA, deployment
16. **Mission 10** (Advanced AI) — Tournament-grade polish
