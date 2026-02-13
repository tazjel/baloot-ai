# Task 14: Hand Shape Evaluator — `hand_shape.py`

## Context
You are building a pure-function AI strategy module for Baloot (Saudi trick-taking card game, 4 players in 2 teams, 32 cards: ranks 7-A in ♠♥♦♣).

**Card objects** have `.rank` (str) and `.suit` (str, one of "♠","♥","♦","♣").
Each player receives 8 cards per round (32 cards / 4 players).

**Modes & rank order:**
- **SUN** (no trump): 7 < 8 < 9 < J < Q < K < 10 < A
- **HOKUM** (trump suit): 7 < 8 < Q < K < 10 < A < 9 < J

## The Problem
Our bidding evaluators (`sun_bidding.py` and `hokum_bidding.py`) score hands using quick tricks, high card points, and trump power — but they don't analyze **hand shape** (distribution pattern). In Baloot, distribution is CRITICAL:

- **4-3-3-3** distribution, while balanced, is BAD because it creates no voids
- **5-3-3-2** is the ideal HOKUM shape (long trump + 2 short suits for ruffing)
- **6-1-1-0** is explosive for HOKUM but risky for SUN
- Voids and singletons in HOKUM = ruffing power
- Balanced hands in SUN = better because you can follow suit everywhere

Here's what the CURRENT `calculate_hokum_strength()` does for distribution (it's basic):
```python
# From hokum_bidding.py lines 80-92 (the ONLY distribution logic):
for s in SUITS:
    if s == trump_suit: continue
    count = len(suits.get(s, []))
    if count == 0:
        score += 4  # Void = can ruff immediately
    elif count == 1:
        score += 2  # Singleton = ruff after 1 round
        if singleton and singleton.rank == 'A':
            score += 2  # Singleton Ace = win trick then void!
```

This is too simplistic — it doesn't consider:
- The PATTERN as a whole (is 5-1-1-1 better than 4-2-2-0 for this trump length?)
- Whether short suits face a good opponent void (risky short suit)
- Long-suit running potential (5+ in a suit with A-K = 3+ extra tricks)
- SUN-specific shape penalties (voids are BAD in Sun!)

## Your Task
Create **`hand_shape.py`** — analyzes distribution pattern and returns adjustments for both Sun and Hokum bidding.

### Required Functions

```python
def evaluate_shape(
    hand: list,            # card objects with .rank, .suit
    mode: str,             # "SUN" or "HOKUM"
    trump_suit: str | None = None,  # only for HOKUM
) -> dict:
```

### Return Format
```python
{
    "pattern": [4, 3, 1, 0],         # sorted desc suit lengths (always 4 elements summing to 8)
    "pattern_label": "4-3-1-0",      # string label
    "shape_type": "UNBALANCED",      # BALANCED / SEMI_BALANCED / UNBALANCED / EXTREME
    "bid_adjustment": +3.5,          # added to bidding score (can be negative)
    "voids": ["♦"],                  # suits with 0 cards
    "singletons": ["♣"],             # suits with exactly 1 card
    "long_suits": [("♥", 4)],        # suits with 4+ cards: [(suit, length)]
    "ruff_potential": 2.0,           # HOKUM only: estimated extra tricks from ruffing
    "long_suit_tricks": 1.5,         # estimated extra tricks from long-suit running
    "reasoning": "4-3-1-0 UNBALANCED: void ♦ + singleton ♣ = 2 ruffs; 4♥ with A-K = 1.5 long tricks"
}
```

### Classification Rules

**Shape types** (based on sorted pattern):
| Pattern | Type | SUN adj | HOKUM adj |
|---------|------|---------|-----------|
| 4-3-3-3 | BALANCED | 0 | -2 (no ruffs possible) |
| 4-4-3-2 | BALANCED | 0 | -1 |
| 5-3-3-2 | SEMI_BALANCED | -1 | +2 (ideal HOKUM) |
| 4-3-2-1 | SEMI_BALANCED | -1 | +2 |
| 5-4-2-2 | SEMI_BALANCED | -2 | +3 |
| 5-3-1-1 | UNBALANCED | -3 | +4 |
| 5-4-3-1 | UNBALANCED | -2 | +3 |
| 6-x-x-x | EXTREME | -4 | +4 to +6 |
| Any with void | UNBALANCED+ | -4 | +5 |

**Ruff potential** (HOKUM only):
- For each non-trump suit with 0 cards: +1.0 ruff (if we have spare trumps)
- For each non-trump suit with 1 card: +0.5 ruff (void after 1 round)
- Cap at (trump_count - top_trump_tricks) — can't ruff with winners

**Long suit tricks:**
- 5-card suit with A: +1.0 extra trick (likely to run once opponents void)
- 5-card suit with A+K: +1.5 extra tricks
- 6-card suit with A: +2.0 extra tricks
- 4-card suit with A+K+10: +0.5 extra trick

### Constraints
- Pure functions, no classes, no external deps beyond `__future__` and `collections`
- Use `from __future__ import annotations`
- Include docstrings
- ~80-110 lines
- Handle: empty hand, fewer than 8 cards (mid-game), None trump_suit
- Constants: `ALL_SUITS = ["♠", "♥", "♦", "♣"]`
