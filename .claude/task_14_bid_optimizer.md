# Task 14: Bid Optimizer — `bid_optimizer.py`

## Context
You are building AI strategy modules for a Baloot (Saudi card game) AI.
The game has 4 players in 2 teams. Cards: 32 (7-A in ♠♥♦♣).
Two modes: **SUN** (no trump, A highest) and **HOKUM** (trump suit, J highest).

**Bidding:** Players choose SUN, HOKUM (pick trump), or PASS.
Doubling (صن/حكم كبير) and bid stealing (قبلة/Gablak) available.

**Rank order:**
- SUN: 7 < 8 < 9 < J < Q < K < 10 < A
- HOKUM: 7 < 8 < Q < K < 10 < A < 9 < J

**Point values:**
- SUN: A=11, 10=10, K=4, Q=3, J=2 (total 130 + last trick bonus)
- HOKUM: J=20, 9=14, A=11, 10=10, K=4, Q=3

We already have these modules:
- `trick_projection.py` → `project_tricks(hand, mode, trump_suit)` → {min_tricks, expected_tricks, max_tricks, quick_tricks, ...}
- `score_pressure.py` → `get_score_pressure(us, them)` → {situation, bid_threshold_adjustment, doubling_bias}
- `score_pressure.py` → `should_gamble(us, them, strength, bid_type)` → bool
- `sun_bidding.py` → existing Sun hand evaluation
- `hokum_bidding.py` → existing Hokum hand evaluation

## Your Task
Create **`bid_optimizer.py`** — the final aggregation layer that calls
the existing modules and produces the actual bid decision.

### Required Functions
```python
def optimize_bid(
    hand: list,                  # list of card objects with .rank and .suit
    position_in_bidding: int,    # 0-3 (0=first to bid)
    us_score: int,               # our team's match score
    them_score: int,             # opponent team's match score
    bids_so_far: list[dict],     # [{"player": "Right", "action": "PASS"}, ...]
    allowed_actions: list[str],  # ["SUN", "HOKUM", "PASS"]
) -> dict:
```

### Return Format
```python
{
    "action": "HOKUM",              # SUN / HOKUM / PASS
    "trump_suit": "♥",             # only if HOKUM
    "confidence": 0.78,
    "should_double": False,         # True if hand is overwhelming
    "should_gablak": False,         # True for bid stealing
    "components": {
        "sun_strength": 0.62,       # raw Sun evaluation
        "hokum_strength": {"♥": 0.81, "♠": 0.45, ...},
        "trick_estimate": 5.2,      # from trick_projection
        "pressure": "TRAILING",     # from score_pressure
        "threshold_adj": -0.08,     # from score_pressure
    },
    "reasoning": "HOKUM ♥: J+9+A trump (5.2 tricks), TRAILING pressure lowers threshold..."
}
```

### Logic to Implement
1. **Evaluate Sun** — quick tricks across all suits, penalize voids, favor balanced
2. **Evaluate Hokum** — for each suit: count trump power (J=20, 9=14), side aces, short suits; pick best trump
3. **Call trick_projection** — get expected tricks for best Hokum and for Sun
4. **Call score_pressure** — get situation + threshold adjustment
5. **Compare** — SUN needs ~4 expected tricks, HOKUM needs ~3.5; adjust thresholds by pressure
6. **Position bonus** — later position = more info = slight confidence boost
7. **Doubling** — if expected_tricks ≥ 6.5 and quick_tricks ≥ 3
8. **Gablak** — if opponents bid and our hand in that mode is superior
9. **Pass** — if neither Sun nor Hokum meet threshold (adjusted by pressure)

### Constraints
- Pure functions, no classes, no external deps beyond the existing modules
- Import trick_projection and score_pressure modules
- Use `from __future__ import annotations`
- Include docstrings
- ~100-140 lines
- Handle edge cases: no allowed actions, empty hand, missing fields
