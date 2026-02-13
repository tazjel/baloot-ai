# Task 16: Follow-Suit Optimizer — `follow_optimizer.py`

## Context
You are building AI strategy modules for a Baloot (Saudi card game) AI.
The game has 4 players in 2 teams. Cards: 32 (7-A in ♠♥♦♣).
Two modes: **SUN** (no trump, A highest) and **HOKUM** (trump suit, J highest).

**Rank order:**
- SUN: 7 < 8 < 9 < J < Q < K < 10 < A
- HOKUM: 7 < 8 < Q < K < 10 < A < 9 < J

**Point values:**
- SUN: A=11, 10=10, K=4, Q=3, J=2
- HOKUM: J=20, 9=14, A=11, 10=10, K=4, Q=3

We have modules for LEADING. Now we need the mirror: optimal play
when we must FOLLOW suit (seats 2, 3, 4 in a trick).

Key Baloot rules for following:
- You MUST follow the led suit if you can
- If void in led suit, you can play ANY card (trump or discard)
- In HOKUM, you MUST trump if you can and are void in led suit
- The trick winner takes the points

## Your Task
Create **`follow_optimizer.py`** — optimizes follow-suit card selection.

### Required Function
```python
def optimize_follow(
    hand: list,                     # card objects with .rank, .suit
    legal_indices: list[int],       # indices of playable cards (pre-filtered by rules)
    table_cards: list[dict],        # cards already played: [{"rank":"A","suit":"♠","position":"Top"}, ...]
    led_suit: str,                  # suit that was led
    mode: str,                      # "SUN" or "HOKUM"
    trump_suit: str | None,
    seat: int,                      # 2, 3, or 4 (position in trick)
    partner_winning: bool,
    partner_card_index: int | None, # which table_card is partner's (0-based)
    trick_points: int,              # total points currently on table
    tricks_remaining: int,          # tricks left in round
    we_are_buyers: bool,
) -> dict:
```

### Return Format
```python
{
    "card_index": 5,
    "tactic": "WIN_CHEAP",    # one of the labels below
    "confidence": 0.82,
    "reasoning": "10♠ beats current Q♠ winner; save A♠ for later"
}
```

### Tactic Labels
| Label | When | Description |
|-------|------|-------------|
| WIN_BIG | I can win AND trick has ≥15 pts | Play cheapest winning card |
| WIN_CHEAP | I can win, low-med points | Win with minimum required card |
| DODGE | Partner is winning | Play lowest legal card, let partner take it |
| FEED_PARTNER | Partner winning + I have point cards | Shed high-value cards to partner |
| TRUMP_IN | Void + have trump + worth it | Ruff with cheapest trump |
| TRUMP_OVER | Opponent already trumped | Over-trump if possible, else discard |
| DESPERATION | Seat 4, opponent winning big pot | Play highest card, must try to win |
| SHED_SAFE | Can't win, partner not winning | Discard lowest-value non-trump card |

### Logic to Implement (priority cascade)
1. **Can I follow suit?** Separate legal cards into same-suit vs off-suit
2. **If following suit:**
   a. Find cheapest card that BEATS current winner (mode-specific rank order)
   b. If partner winning → DODGE (play lowest) or FEED_PARTNER (shed points ≥10)
   c. If I can win and trick_points ≥ 15 → WIN_BIG
   d. If I can win and seat == 4 → WIN_CHEAP (last to play, guaranteed)
   e. If I can win but seat 2/3 → WIN_CHEAP only if my card is very high
   f. If I can't win → SHED_SAFE (lowest value card)
3. **If void (off-suit):**
   a. In HOKUM: if have trump → check if worth trumping
      - Opponent winning + trick_points ≥ 10 → TRUMP_IN (cheapest trump)
      - Another opponent already trumped → TRUMP_OVER if I can beat it
      - Partner winning → DODGE (don't waste trump)
   b. SHED_SAFE: discard lowest-value card, prefer creating voids

### Helper needed
```python
def _beats(card_rank: str, current_winner_rank: str, mode: str) -> bool:
    """Does card_rank beat current_winner_rank in the given mode?"""
```

### Constraints
- Pure functions, no classes, no external deps
- Use `from __future__ import annotations`
- Include docstrings
- ~120-160 lines
- Handle edge cases: single legal card, all trump hand, seat 4 auto-win
