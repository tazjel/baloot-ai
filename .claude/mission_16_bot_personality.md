# Mission 16: "The Mind" — Bot Personality & Difficulty System

## Goal
Give players varied, engaging opponents by adding 4 bot personalities and 4 difficulty levels.

## Deliverables

### 16.1 Personality Profiles (`ai_worker/strategies/personality.py`)
Pure function: `apply_personality(base_decision, profile, context) -> modified_decision`

| Profile | Arabic | Bidding | Playing |
|---------|--------|---------|---------|
| Aggressive | لعّيب | -15% threshold | Prefer trump leads, chase Kaboot at 5+ tricks |
| Conservative | حذر | +20% threshold | Protect points, safe leads, never double unless certain |
| Tricky | مخادع | Variable | False signals 30%, underplay early, surprise late |
| Balanced | متوازن | Default | No modifications (baseline) |

### 16.2 Difficulty Levels (`ai_worker/strategies/difficulty.py`)
Pure function: `apply_difficulty(recommendations, level) -> filtered_recommendations`

| Level | Card Tracking | Random Play | Kaboot | Endgame Solver |
|-------|--------------|-------------|--------|----------------|
| Easy | Forgets 40% | 15% random | Never | Off |
| Medium | Occasional miss 10% | 10% suboptimal | Passive | Off |
| Hard | Full tracking | Optimal | Active | On |
| Khalid (خالد) | Perfect | Optimal+ | Aggressive | On + squeeze |

### 16.3 Wiring
- sun.py/hokum.py: Apply personality + difficulty before returning final decision
- bidding.py: Apply personality to thresholds, difficulty to evaluation quality
- Frontend: Pre-game difficulty selector with personality preview

### 16.4 Verification
- 100 games per difficulty: Easy loses ~70%, Medium ~50%, Hard ~30%, Khalid ~15%
- Tests: `tests/bot/test_personality.py`, `tests/bot/test_difficulty.py`

## Key Constraint
- personality.py and difficulty.py are pure functions — no classes, no cross-imports
- They receive the final recommendation from brain and modify it — don't change brain internals
