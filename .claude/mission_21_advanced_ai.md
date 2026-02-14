# Mission 21: "The Brain Surgeon" — Advanced AI Intelligence

## Goal
Make the bot play at tournament-grade level with probabilistic memory, score-aware strategy, endplay detection, and a self-play evaluation system.

## Deliverables

### 21.1 Probabilistic Memory (addresses TODO in memory.py:52)
- Replace binary void tracking with `{player: {suit: float}}` probability distributions
- Update on each trick: follow suit → increase P, discard → decrease, trump → set suit P=0
- Bayesian priors from bid info (Hokum ♠ → P(strong ♠) = 0.85) and hand shape
- Wire into lead_selector, follow_optimizer, trump_manager, defense_plan

### 21.2 Score-Aware Play (`ai_worker/strategies/components/score_context.py`)
- `get_score_context(team_scores, match_scores)` → {phase, aggression_mod, risk_tolerance}
- EARLY (0-50), MID (50-100), LATE (100-145), MATCH_POINT (145+)
- Safety play: Ahead 10+ GP and 5+ tricks → protect lead, play low
- Desperation: Behind 100+ match → -25% bid thresholds, pursue Kaboot at 30%, always double
- Match point: 145+ → ultra-conservative, never risk Khasara

### 21.3 Endplay & Squeeze Detection
- Throw-in: At 2-3 cards, detect forced lead into our strong suit
- Trump squeeze: Cashing trumps forces opponent to discard winners
- Wire into endgame_solver as preferred minimax nodes
- Test: 10 handcrafted endgame positions

### 21.4 Self-Play Evaluation (`scripts/self_play.py`)
- Run N matches between 4 bots, record all decisions + outcomes
- ELO rating system (start 1500)
- A/B test: Compare configurations over 500 games with significance
- Threshold tuner: Binary search for optimal brain cascade threshold
- HTML dashboard: Win rates, ELO progression, GP averages, Kaboot frequency

## Key Constraint
- score_context.py is a pure function module (no classes)
- Self-play harness uses existing Game class + bot agent, no external dependencies
- Probabilistic memory must be backward-compatible (binary void still available as fallback)
