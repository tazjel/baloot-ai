# Task 18: Void Creator — `void_creator.py`

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

We have `discard_logic.py` that handles REACTIVE discarding (when already void in the led suit):
```python
def choose_discard(
    hand: list, mode: str, trump_suit: str | None = None,
    partner_winning: bool = False, trick_points: int = 0,
) -> dict:
    # Returns {card_index, reasoning} — picks what to throw away
    # Has basic "create void via shortest suit" but only DURING a discard
```

We also have `trump_manager.py` that manages when to lead/hold trumps:
```python
def manage_trumps(hand, trump_suit, my_trumps, enemy_trumps_estimate, ...) -> dict:
    # Returns {action, lead_trump, reasoning} — controls trump timing
```

**Key gap:** No module PLANS void creation proactively during the LEAD phase.
Currently the bot picks leads based on master cards, suit length, and opponent voids — 
but never thinks "I should lead my lone ♦7 to empty that suit so I can ruff ♦ later."

## What "Void Creation" Means in Baloot

In HOKUM mode, when you are void in a side suit and that suit is led by an opponent, you can play a trump card to win the trick (this is called "ruffing" / الأكل بالحكم). This is one of the most powerful plays in Baloot.

**To set up a ruff:**
1. You must be VOID in the target side suit (0 cards in that suit)
2. You must still HAVE trump cards to ruff with
3. An opponent must still have cards in that suit to lead it (or partner leads it for you)

So the strategy is: if you hold 1-2 cards in a side suit AND you have trumps, lead those side-suit cards early to create a void, then ruff later.

## Your Task
Create **`void_creator.py`** — a proactive void engineering advisor for LEAD selection.

### Required Function
```python
def plan_void(
    hand: list,                       # card objects with .rank, .suit
    mode: str,                        # "SUN" or "HOKUM"
    trump_suit: str | None,           # trump suit if HOKUM, None if SUN
    tricks_remaining: int,            # how many tricks left (1-8)
    enemy_void_suits: list[str],      # suits where opponents are void
    partner_void_suits: list[str],    # suits where partner is void
    we_are_buyers: bool,              # True if our team won the bid
) -> dict | None:
```

### Return Format
```python
{
    "card_index": 2,                  # index into hand — the card to lead
    "strategy": "STRIP_SINGLETON",    # one of the strategies below
    "confidence": 0.75,               # 0.0-1.0
    "reasoning": "Lead 7♦ (singleton) to void ♦ — have 3 trumps for ruffing",
    "void_suit": "♦",                # which suit we're trying to void
    "estimated_ruff_value": 14,       # estimated points we could gain per ruff
}
```
Return `None` if void creation is not worthwhile (SUN mode, no trumps, too late, etc.)

### Strategies to Implement
1. **STRIP_SINGLETON** — Lead the lone card in a 1-card side suit.
   - Requirements: exactly 1 card in a non-trump suit, ≥1 trump remaining
   - Confidence: 0.8 if we have ≥2 trumps, 0.6 if only 1 trump
   - Best when: tricks_remaining ≥ 3 (need time to ruff)

2. **STRIP_DOUBLETON** — Lead from a 2-card side suit (lead the LOW card first).
   - Requirements: exactly 2 cards in a non-trump suit, ≥2 trumps remaining
   - We'll need 2 tricks to void, so only do this early (tricks_remaining ≥ 5)
   - Lead the LOWER-ranked card first (protect the higher one for a second potential strip)
   - Confidence: 0.65

3. **PARTNER_RUFF_SETUP** — Lead a suit where PARTNER is void (partner can ruff).
   - Requirements: partner is void in a side suit, partner likely has trumps
   - Lead the HIGHEST card in that suit (we're going to lose it anyway, might as well lead strong)
   - Wait — actually lead the LOWEST card if opponents might over-ruff partner
   - Confidence: 0.7

4. **SKIP** — Don't create a void. Return `None` in these cases:
   - Mode is SUN (no trumps to ruff with)
   - No trumps in hand (can't ruff even if void)
   - tricks_remaining ≤ 2 (too late to set up)
   - All side suits have 3+ cards (no short suits to exploit)
   - The target suit is already voided by an enemy (they'll trump our lead!)

### Logic Rules
1. **Only applicable in HOKUM** — return `None` immediately if mode == "SUN"
2. **Count trumps first** — if we have 0 trumps, return `None` (can't ruff)
3. **Find void candidates** — group hand by suit, find suits with 1-2 cards (excluding trump)
4. **Filter out dangerous voids** — if a suit is in `enemy_void_suits`, skip it:
   - Leading a suit where an enemy is void means THEY ruff US, not the other way around
5. **Prioritize by:**
   - Singleton > Doubleton (fewer tricks to void)
   - Lower-value cards first (losing a 7 is cheaper than losing a K)
   - More trumps = higher confidence
   - Earlier game = higher confidence
6. **Estimated ruff value** — approximate points per ruff:
   - If we have J♥ (trump jack): use 20 as base
   - High trump (9, A): 14, 11
   - Low trump (7, 8, Q, K, 10): use the average of likely trick points = 8
   - Simplification: just use `max(PTS_HOKUM.get(t.rank, 0) for t in trump_cards)` for the ruff card's value, 
     PLUS the average side-suit trick value (~8 pts) as estimated_ruff_value
7. **Break ties** — when multiple void candidates exist, prefer:
   - The suit with the lowest total point value in our cards (cheapest to strip)
   - Then shortest suit first (singleton before doubleton)

### Constraints
- Pure functions only — no classes, no external imports beyond `__future__` and stdlib
- Use `from __future__ import annotations`
- Include docstrings on all public functions
- ~80-120 lines total
- Handle: empty hand, None trump_suit, no valid void targets gracefully
- Return `None` for any situation where void creation is suboptimal
- Constants: `ALL_SUITS = ["♠","♥","♦","♣"]`
- Point maps: `PTS_HOKUM = {"J":20,"9":14,"A":11,"10":10,"K":4,"Q":3}`
