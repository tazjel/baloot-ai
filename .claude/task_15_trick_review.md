# Task 15: Trick Review Engine — `trick_review.py`

## Context
You are building a pure-function AI strategy module for Baloot (Saudi trick-taking card game, 4 players in 2 teams, 32 cards: ranks 7-A in ♠♥♦♣).

**Card objects** have `.rank` (str) and `.suit` (str, one of "♠","♥","♦","♣").

**Modes & rank order:**
- **SUN** (no trump): 7 < 8 < 9 < J < Q < K < 10 < A
- **HOKUM** (trump suit): 7 < 8 < Q < K < 10 < A < 9 < J

**Point values:**
- SUN: A=11, 10=10, K=4, Q=3, J=2, rest=0
- HOKUM: J=20, 9=14, A=11, 10=10, K=4, Q=3, rest=0

**Positions:** "Bottom", "Right", "Top", "Left". Teams: Bottom+Top vs Right+Left.

## The Problem
Currently, the AI makes decisions trick-by-trick with NO memory of what happened in earlier tricks beyond raw card tracking. After trick 4, the game state is very different from trick 1 — but nothing reviews the pattern of results to adapt strategy.

For example:
- If opponents trumped our Ace in trick 2, we should STOP leading that suit
- If partner has been winning tricks in ♥, we should keep feeding ♥
- If we've lost 3 of 4 tricks, our strategy should shift from "winning" to "damage control"
- If opponents are discarding big points to each other, they're cooperating well (raise danger)

## Actual Trick History Format
From `game_state['currentRoundTricks']`:
```python
[
    {
        "leader": "Bottom",
        "cards": [
            {"card": {"rank": "A", "suit": "♠"}, "playedBy": "Bottom"},
            {"card": {"rank": "7", "suit": "♠"}, "playedBy": "Right"},
            {"card": {"rank": "K", "suit": "♠"}, "playedBy": "Top"},
            {"card": {"rank": "9", "suit": "♥"}, "playedBy": "Left"},  # trumped!
        ],
        "winner": "Left"
    },
    ...
]
```

## Your Task
Create **`trick_review.py`** — analyzes completed tricks and returns strategic adjustments.

### Required Function
```python
def review_tricks(
    my_position: str,          # "Bottom", "Right", "Top", "Left"
    trick_history: list[dict], # format shown above
    mode: str,                 # "SUN" or "HOKUM"
    trump_suit: str | None = None,
    we_are_buyers: bool = True,
) -> dict:
```

### Return Format
```python
{
    "our_tricks": 3,
    "their_tricks": 2,
    "momentum": "WINNING",           # WINNING / LOSING / TIED / COLLAPSING
    "points_won_by_us": 42,
    "points_won_by_them": 28,
    "strategy_shift": "NONE",        # NONE / CONSERVATIVE / AGGRESSIVE / DAMAGE_CONTROL
    "suit_results": {
        "♠": {"led": 2, "won": 1, "lost": 1, "points_lost": 11, "got_trumped": True},
        "♥": {"led": 1, "won": 1, "lost": 0, "points_lost": 0, "got_trumped": False},
        ...
    },
    "avoid_suits": ["♠"],            # suits where we got trumped or consistently lost
    "strong_suits": ["♥"],           # suits where we consistently won
    "partner_contribution": 0.6,     # 0-1: how often partner won tricks they led
    "opponent_cooperation": 0.4,     # 0-1: how often opponents fed points to each other
    "reasoning": "WINNING 3-2, +14pts; avoid ♠ (trumped trick 3); partner strong in ♥"
}
```

### Logic to Implement

1. **Score tracking:** Sum point values of cards in each trick, assigned to winning team
2. **Momentum classification:**
   - WINNING: our_tricks > their_tricks AND we won the last trick
   - LOSING: their_tricks > our_tricks AND they won the last trick
   - COLLAPSING: we lost the last 2+ tricks in a row
   - TIED: otherwise
3. **Strategy shift:**
   - If tricks_played >= 4 and we're losing by 2+: DAMAGE_CONTROL
   - If we're winning by 2+ and we_are_buyers: CONSERVATIVE (protect the lead)
   - If we're losing and we_are_buyers: AGGRESSIVE (must win to make bid)
   - Otherwise: NONE
4. **Suit analysis:** For each suit that was led:
   - Count how many times it was led, won by us, lost by us
   - Track if our side ever got trumped in that suit
   - Calculate total points we lost in tricks where that suit was led
5. **Avoid suits:** Suits where got_trumped=True OR win_rate < 0.3
6. **Strong suits:** Suits where win_rate >= 0.7 and led at least once
7. **Partner contribution:** (tricks partner won as leader) / (tricks partner led), or 0.5 default
8. **Opponent cooperation:** Count tricks where an opponent discarded 10+ point card to their winning partner / total opponent-won tricks

### Constraints
- Pure functions, no classes, no external deps beyond `__future__`
- Use `from __future__ import annotations`
- Include docstrings
- ~100-130 lines
- Handle: empty trick_history, partial tricks, missing fields
- Constants: `POSITIONS = ["Bottom", "Right", "Top", "Left"]`
