# Task 13: Opponent Model — `opponent_model.py`

## Context
You are building AI strategy modules for a Baloot (Saudi card game) AI.
The game has 4 players in 2 teams. Cards: 32 (7-A in ♠♥♦♣).
Two modes: **SUN** (no trump, A highest) and **HOKUM** (trump suit, J highest).

**Rank order:**
- SUN: 7 < 8 < 9 < J < Q < K < 10 < A
- HOKUM: 7 < 8 < Q < K < 10 < A < 9 < J (trump J=20pts, 9=14pts)

**Point values:**
- SUN: A=11, 10=10, K=4, Q=3, J=2
- HOKUM: J=20, 9=14, A=11, 10=10, K=4, Q=3

We have `partner_read.py` that infers what our PARTNER holds.
We need the mirror: a module that tracks what OPPONENTS likely hold
by watching their plays, bids, voids, and trumping patterns.

## Existing Partner Read (for reference)
```python
def read_partner(
    partner_position, bid_history, trick_history,
    mode, trump_suit=None
) -> dict:
    # Returns: likely_strong_suits, likely_void_suits,
    #          estimated_trumps, has_high_trumps, confidence, detail
```

## Your Task
Create **`opponent_model.py`** — a pure-function module (no classes, no ML).

### Required Function
```python
def model_opponents(
    my_position: str,           # "Bottom", "Right", "Top", "Left"
    bid_history: list[dict],    # [{"player": "Right", "action": "PASS"}, ...]
    trick_history: list[dict],  # [{"leader": "Top", "cards": [{"rank":"A","suit":"♠","position":"Top"},...], "winner": "Top"}, ...]
    mode: str,                  # "SUN" or "HOKUM"
    trump_suit: str | None = None,
) -> dict:
```

### Return Format
```python
{
    "left_opponent": {
        "likely_void_suits": ["♠"],
        "estimated_trumps": 2,       # HOKUM only
        "has_high_trumps": True,     # J or 9
        "strength_by_suit": {"♠": -5.0, "♥": 2.0, ...},
        "play_style": "AGGRESSIVE",  # AGGRESSIVE / PASSIVE / UNKNOWN
        "danger_level": 0.7,         # 0–1, how threatening this opponent is
    },
    "right_opponent": { ... same structure ... },
    "combined_danger": 0.65,
    "safe_lead_suits": ["♦"],        # suits where neither opp is void/strong
    "avoid_lead_suits": ["♠"],       # suits where an opp is void + has trump
    "reasoning": "Right void ♠, has J♥ trump; Left passive..."
}
```

### Logic to Implement
1. **Identify opponents** — the two players who are NOT me and NOT my partner
2. **Bid inference** — HOKUM bid → strong trump; SUN bid → balanced; PASS → weak
3. **Void detection** — didn't follow suit → void in that suit
4. **Trump tracking** (HOKUM) — count trumps played, detect J/9
5. **Strength scoring** — high leads from a suit = strong; low discards = weak
6. **Play style** — count aggressive plays (trumping, high leads) vs passive
7. **Danger level** — composite of trump count, strong suits, aggressiveness
8. **Safe/avoid lead** — cross-reference voids + trump holdings

### Constraints
- Pure functions, no classes, no external deps
- Use `from __future__ import annotations`
- Include docstrings
- ~100-130 lines
- Handle edge cases: empty history, unknown positions, missing fields
