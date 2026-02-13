# Task 13: Opponent Model — `opponent_model.py`

## Context
You are building a pure-function AI strategy module for Baloot (Saudi trick-taking card game, 4 players in 2 teams, 32 cards: ranks 7-A in ♠♥♦♣).

**Card objects** have `.rank` (str) and `.suit` (str, one of "♠","♥","♦","♣").

**Modes & rank order:**
- **SUN** (no trump): 7 < 8 < 9 < J < Q < K < 10 < A
- **HOKUM** (trump suit): 7 < 8 < Q < K < 10 < A < 9 < J (in trump suit, J=20pts, 9=14pts)

**Point values:**
- SUN: A=11, 10=10, K=4, Q=3, J=2, rest=0
- HOKUM: J=20, 9=14, A=11, 10=10, K=4, Q=3, rest=0

**Positions:** "Bottom", "Right", "Top", "Left". Teams: Bottom+Top vs Right+Left.

## What Already Exists (DO NOT duplicate)
We have `partner_read.py` that infers PARTNER holdings. Here is the EXACT interface for reference:

```python
def read_partner(
    partner_position: str, bid_history: list[dict], trick_history: list[dict],
    mode: str, trump_suit: str | None = None,
) -> dict:
    # Returns:
    # {
    #     "likely_strong_suits": ["♥", "♠"],     # sorted by strength score
    #     "likely_void_suits": ["♦"],              # suits they can't follow
    #     "estimated_trumps": 2,                   # HOKUM only
    #     "has_high_trumps": True,                  # J or 9
    #     "confidence": 0.42,                       # 0–1, scaled by evidence count
    #     "detail": "ev=5 | bid HOKUM ♥; ruff ♦ w/9♥"
    # }
```

We also have `card_tracker.py` (a class, NOT pure functions) that tracks:
- `get_void_players(suit)` → positions void in that suit
- `get_remaining_cards(suit)` → unseen cards
- `is_my_card_master(card, mode)` → bool

## Actual Data Shapes from the Game

**bid_history** looks like:
```python
[
    {"player": "Bottom", "action": "PASS"},
    {"player": "Right", "action": "HOKUM", "suit": "♥"},
    {"player": "Top", "action": "PASS"},
    {"player": "Left", "action": "PASS"},
]
```

**trick_history** (from `game_state['currentRoundTricks']`) looks like:
```python
[
    {
        "leader": "Right",
        "cards": [
            {"card": {"rank": "J", "suit": "♥"}, "playedBy": "Right"},
            {"card": {"rank": "7", "suit": "♥"}, "playedBy": "Top"},
            {"card": {"rank": "A", "suit": "♥"}, "playedBy": "Left"},
            {"card": {"rank": "8", "suit": "♥"}, "playedBy": "Bottom"},
        ],
        "winner": "Right"
    },
    ...
]
```
Note: In trick_history, each card entry has `"card"` (dict with rank/suit) and `"playedBy"` (position string).

## Your Task
Create **`opponent_model.py`** — mirrors `read_partner` but tracks BOTH opponents.

### Required Function
```python
def model_opponents(
    my_position: str,           # "Bottom", "Right", "Top", "Left"
    bid_history: list[dict],    # format shown above
    trick_history: list[dict],  # format shown above (list of trick dicts)
    mode: str,                  # "SUN" or "HOKUM"
    trump_suit: str | None = None,
) -> dict:
```

### Return Format
```python
{
    "opponents": {
        "Right": {                         # opponent position
            "void_suits": ["♠"],           # suits they failed to follow
            "estimated_trumps": 2,         # HOKUM only, count of trumps seen/inferred
            "has_high_trumps": True,       # played J or 9 of trump
            "strength_by_suit": {"♠": -5.0, "♥": 2.0, "♦": 0.0, "♣": 1.0},
            "play_style": "AGGRESSIVE",    # AGGRESSIVE / PASSIVE / UNKNOWN
            "danger_level": 0.7,           # 0–1 composite threat score
        },
        "Left": { ... },                   # same structure
    },
    "safe_lead_suits": ["♦"],              # suits where NO opponent is void or strong
    "avoid_lead_suits": ["♠"],             # suits where an opp is void (will trump/discard)
    "combined_danger": 0.65,               # average of both opponents' danger
    "reasoning": "Right void ♠ + has J♥; Left passive, no masters seen"
}
```

### Logic to Implement
1. **Identify opponents** — given my_position, opponents are the two NON-partner positions  
   (partner = position + 2 mod 4 in the POSITIONS list)
2. **Bid inference** — HOKUM bid → strong trump (strength +3), SUN bid → balanced (+1 all suits), PASS → weak (-0.3 all)
3. **Trick analysis** — for each trick, for each opponent's card:
   - If they didn't follow the led suit → mark void in that suit (strength = -5)
   - If they played trump when void → count trump, check for J/9
   - If they LED a high card (A, 10, K) → strong in that suit (+2)
   - If they LED a low card (7, 8) → weak in that suit (-0.5)
   - If they followed with a high card → moderate strength (+1)
4. **Play style** — count aggressive plays (leading high, trumping) vs passive (low discards). Ratio > 0.6 = AGGRESSIVE, < 0.4 = PASSIVE, else UNKNOWN
5. **Danger level** — composite: (trump_count * 0.15) + (strong_suits * 0.1) + (style_score * 0.2), capped at 1.0
6. **Safe/avoid leads** — a suit is "avoid" if ANY opponent is void in it; "safe" if neither opponent is void AND neither has strength > 1.0 in it

### Constraints
- Pure functions only — no classes, no external imports beyond `__future__` and stdlib
- Use `from __future__ import annotations`
- `from collections import defaultdict` is OK
- Include docstrings on all public functions
- ~100-130 lines total
- Handle: empty trick_history, missing fields, unknown positions gracefully
- Constants: `POSITIONS = ["Bottom", "Right", "Top", "Left"]`, `ALL_SUITS = ["♠", "♥", "♦", "♣"]`
