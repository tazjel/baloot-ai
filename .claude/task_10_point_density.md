Write a single self-contained Python module: `point_density.py`

This is a Point Density Evaluator for a Baloot card game AI.
It evaluates how many points are at stake in the current trick
and tells the bot whether to commit high cards or play low.

Return ONLY the Python code, no explanation.

## Function Signatures

```python
def evaluate_trick_value(
    table_cards: list[dict],  # [{"rank": "A", "suit": "♠", "playedBy": "Bottom"}, ...]
    mode: str,                # "SUN" or "HOKUM"
) -> dict:
    # Returns:
    # {
    #   "current_points": int,       # points already on the table
    #   "density": "EMPTY" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
    #   "worth_fighting": bool,      # should we commit high cards?
    #   "point_cards_on_table": int,  # count of point-carrying cards
    # }


def should_play_high(
    table_cards: list[dict],
    my_card_rank: str,        # rank being considered (e.g. "A", "10", "K")
    mode: str,                # "SUN" or "HOKUM"
    partner_is_winning: bool,
    cards_remaining: int,     # how many cards left in hand (1-8)
) -> dict:
    # Returns:
    # {
    #   "play_high": bool,
    #   "reasoning": str,
    # }
```

## Constants (copy exactly)

```python
POINT_VALUES_SUN = {"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2, "9": 0, "8": 0, "7": 0}
POINT_VALUES_HOKUM = {"J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3, "8": 0, "7": 0}
```

## Density Thresholds

| Points on Table | Density | worth_fighting |
|----------------|---------|----------------|
| 0 | EMPTY | False |
| 1–6 | LOW | False |
| 7–15 | MEDIUM | True (if not partner winning) |
| 16–25 | HIGH | True |
| 26+ | CRITICAL | True (always) |

## should_play_high Logic

1. If `partner_is_winning` AND density < HIGH → `play_high = False` (don't override partner)
2. If density is CRITICAL → `play_high = True` (always fight for 26+ pt tricks)
3. If `cards_remaining <= 2` → `play_high = True` (endgame, every point matters)
4. If density is EMPTY and card is A or 10 → `play_high = False` (don't waste high cards on empty tricks)
5. If density is HIGH and card is A, 10, K, J → `play_high = True`
6. Default: follow density.worth_fighting

## Requirements
- Pure functions, no imports beyond stdlib
- Include module docstring
- table_cards entries are dicts with "rank" and "suit" keys
- Handle empty table_cards (return EMPTY, 0 points)
