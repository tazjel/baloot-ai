# Task 16: Cooperative Play Engine — `cooperative_play.py`

## Context
You are building a pure-function AI strategy module for Baloot (Saudi trick-taking card game, 4 players in 2 teams, 32 cards: ranks 7-A in ♠♥♦♣).

**Card objects** have `.rank` (str) and `.suit` (str, one of "♠","♥","♦","♣").

**Modes & rank order:**
- **SUN** (no trump): 7 < 8 < 9 < J < Q < K < 10 < A
- **HOKUM** (trump suit): 7 < 8 < Q < K < 10 < A < 9 < J

**Point values:**
- SUN: A=11, 10=10, K=4, Q=3, J=2, rest=0
- HOKUM: J=20, 9=14, A=11, 10=10, K=4, Q=3, rest=0

## The Problem
We have `partner_read.py` that INFERS partner's holdings, and `follow_optimizer.py` that selects follow-suit cards — but nothing bridges them. The follow optimizer uses `partner_winning: bool` as a simple flag, but doesn't consult the partner read to make SMART cooperative decisions.

**What `partner_read.py` returns** (already implemented):
```python
{
    "likely_strong_suits": ["♥", "♠"],     # sorted by strength score
    "likely_void_suits": ["♦"],              # suits they can't follow
    "estimated_trumps": 2,                   # HOKUM only
    "has_high_trumps": True,                  # J or 9
    "confidence": 0.42,                       # 0–1, scaled by evidence count
    "detail": "ev=5 | bid HOKUM ♥; ruff ♦ w/9♥"
}
```

**What `follow_optimizer.py` uses** (it DOESN'T read partner_info):
```python
def optimize_follow(
    hand, legal_indices, table_cards, led_suit, mode,
    trump_suit, seat, partner_winning,          # ← simple bool, no partner intelligence
    partner_card_index, trick_points,
    tricks_remaining, we_are_buyers,
) -> dict:
    # Returns: {card_index, tactic, confidence, reasoning}
```

The gap: There's no module that takes partner_read OUTPUT and produces cooperative play DECISIONS for both leading and following situations.

## What This Module Should Do
Given what we know about our partner's hand, make COOPERATIVE decisions:

### When Leading:
1. **Feed partner's strong suit** — if partner is strong in ♥, lead low ♥ to let them win
2. **Avoid partner's void suits** — if partner is void in ♦, don't lead ♦ (they can't follow, opponents might win)
3. **Draw trump for partner** — in HOKUM, if partner has no high trumps but has side winners, draw enemy trumps first
4. **Set up partner's run** — if partner has long suit, lead that suit to help exhaust opponents

### When Following:
5. **Sacrifice for partner** — if partner led a suit they're strong in and opponent might beat them, play YOUR high card to protect partner
6. **Smart discard** — when void in led suit, discard from suits partner is ALSO void in (no loss) rather than partner's strong suits
7. **Trump support** — in HOKUM, if partner led trump to draw, follow with your lowest trump (don't waste J/9)

## Your Task
Create **`cooperative_play.py`** — takes partner_read output and game state, returns cooperative adjustments.

### Required Functions

```python
def get_cooperative_lead(
    hand: list,                     # card objects with .rank, .suit
    partner_info: dict,             # from partner_read.py (format above)
    mode: str,                      # "SUN" or "HOKUM"
    trump_suit: str | None = None,
    tricks_remaining: int = 8,
    we_are_buyers: bool = True,
) -> dict | None:
```

**Returns** (or None if no cooperative play is better than default):
```python
{
    "card_index": 3,
    "strategy": "FEED_STRONG",      # FEED_STRONG / AVOID_VOID / DRAW_TRUMP / SETUP_RUN
    "confidence": 0.7,
    "reasoning": "Partner strong in ♥ (conf 0.42) — lead 8♥ to let them win"
}
```

```python
def get_cooperative_follow(
    hand: list,                     # card objects
    legal_indices: list[int],       # pre-filtered by rules engine
    partner_info: dict,             # from partner_read.py
    led_suit: str,                  # suit of the opening card
    mode: str,                      # "SUN" or "HOKUM"
    trump_suit: str | None = None,
    partner_winning: bool = False,
    trick_points: int = 0,
) -> dict | None:
```

**Returns** (or None if default follow_optimizer is fine):
```python
{
    "card_index": 5,
    "tactic": "SMART_DISCARD",      # SACRIFICE / SMART_DISCARD / TRUMP_SUPPORT
    "confidence": 0.65,
    "reasoning": "Void in led suit — discard 7♦ (partner also void ♦) instead of ♠ (partner strong)"
}
```

### Logic Details

**`get_cooperative_lead():`**
1. If `partner_info` is None or confidence < 0.25: return None (not enough info)
2. **FEED_STRONG:** Find suits in `partner_info['likely_strong_suits']` where we hold a low card (rank_index <= 3). Lead the lowest in the strongest suit. Confidence = partner_confidence * 0.8
3. **AVOID_VOID:** Filter out suits in `partner_info['likely_void_suits']` from consideration — these are suits partner can't follow, likely benefiting opponents
4. **DRAW_TRUMP** (HOKUM only): If `partner_info['has_high_trumps'] == False` and `partner_info['estimated_trumps'] >= 2`, partner has weak trumps. If WE have a high trump (J, 9, or A), lead it to strip enemy trumps and protect partner
5. **SETUP_RUN:** If a suit appears in both `likely_strong_suits` and we hold 3+ cards in it, lead high from that suit to establish a run

**`get_cooperative_follow():`**
1. If `partner_info` is None or confidence < 0.2: return None
2. **SACRIFICE**: If partner_winning and trick_points >= 15 and we have a beater that's NOT in partner's strong suits, play it
3. **SMART_DISCARD**: When void in led_suit (no legal same-suit cards), prefer discarding from:
   - First choice: suits partner is ALSO void in (discarding from `likely_void_suits`)
   - Second choice: low cards from any suit NOT in `likely_strong_suits`
   - Avoid: discarding from partner's strong suits (they need us to hold those)
4. **TRUMP_SUPPORT**: In HOKUM, if partner led trump and partner_info shows they have high trumps, follow with our lowest trump to let partner's J/9 win

### Utility Constants
```python
ORDER_SUN = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]
ALL_SUITS = ["♠", "♥", "♦", "♣"]
_PTS_SUN = {"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2}
_PTS_HOKUM = {"J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3}
```

### Constraints
- Pure functions, no classes, no external deps beyond `__future__`
- Use `from __future__ import annotations`
- Include docstrings on both public functions
- ~120-150 lines total
- Return None freely — this module should only override defaults when confident
- Handle: None partner_info, empty hand, empty legal_indices, missing dict keys
