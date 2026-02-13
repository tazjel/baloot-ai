# Task 17: Seat Strategy — `seat_strategy.py`

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

We have `follow_optimizer.py` that does basic follow-suit optimization with an 8-tactic cascade.
It handles winning/ducking/point-feeding but its seat awareness is minimal — it doesn't consider:
- Which specific players sit AFTER us and whether they're opponents or partner
- What high cards remain unplayed in the led suit (card counting)
- Whether to sacrifice a strong card now to set up a later trick

We also have inline seat logic in `sun.py` (lines 546-578) and `hokum.py` (lines 517-542) that uses hardcoded thresholds like `trick_points >= 10` and `trick_points >= 15` with no deeper reasoning.

## Actual Data Shapes from the Game

**table_cards** (cards already played in this trick):
```python
[
    {"rank": "K", "suit": "♥", "playedBy": "Right"},   # 1st card (leader)
    {"rank": "Q", "suit": "♥", "playedBy": "Top"},     # 2nd card
    # ... (0-3 cards depending on seat)
]
```

**remaining_high_cards** — a list of ranks still unplayed in the led suit:
```python
["A", "10"]  # Only Ace and 10 of hearts haven't been played yet
```
This comes from our `card_tracker` which tracks all played cards.

## Your Task
Create **`seat_strategy.py`** — a specialized positional play advisor for 2nd, 3rd, and 4th seat.

### Required Function
```python
def advise_seat_play(
    hand: list,                    # card objects with .rank, .suit
    legal_indices: list[int],      # indices of cards we can legally play
    table_cards: list[dict],       # cards already played: [{rank, suit, playedBy}, ...]
    seat: int,                     # 2, 3, or 4 (our position in this trick)
    led_suit: str,                 # suit that was led
    mode: str,                     # "SUN" or "HOKUM"
    trump_suit: str | None,        # trump suit if HOKUM, None if SUN
    partner_winning: bool,         # is partner currently winning the trick
    trick_points: int,             # total point value on the table so far
    remaining_high_cards: list[str], # ranks still unplayed in led suit (from card counting)
    opponent_after_us: bool,       # True if an opponent plays after us
) -> dict | None:
```

### Return Format
```python
{
    "card_index": 3,               # index into hand
    "tactic": "FINESSE_4TH",      # one of the tactics below
    "confidence": 0.85,            # 0.0-1.0
    "reasoning": "4th seat: win with Q♥ (minimum winner, A♥ already played)"
}
```
Return `None` if no strong positional advice (let caller fall through to heuristics).

### Tactics to Implement
1. **FINESSE_4TH** — 4th seat: play the minimum card that wins. Confidence 0.9 (guaranteed last).
2. **COVER_3RD** — 3rd seat: if trick has high points (≥10) and we can win, play our best winner. 
   But check: if remaining_high_cards shows the 4th player could still beat us, hedge carefully.
3. **DUCK_2ND** — 2nd seat: intentionally play low to let partner handle it. Only when:
   - trick_points < 10 AND partner plays after an opponent (i.e., partner has positional advantage)
   - We don't have the master (guaranteed winner)
4. **COMMIT_2ND** — 2nd seat: commit a strong card when trick value is high (≥15) or we hold the master.
5. **SAFE_FEED** — Partner is winning: feed maximum points without overtaking.
   Calculate the highest point card we can play that is LOWER in rank than partner's winning card.
6. **FORCED_OVERTAKE** — Partner is winning but all our cards beat partner's. Play lowest winner reluctantly.
7. **POINT_PROTECT** — Can't win at all: play our lowest-point card to minimize loss.
8. **HEDGE_3RD** — 3rd seat: play an intermediate card when remaining_high_cards shows 
   4th player has a potential killer (don't waste our best card if it'll get beaten anyway).

### Logic Rules
1. **4th seat** is special — we see ALL other cards. If we can win, always win with minimum winner. 
   If we can't win, always protect points.
2. **3rd seat** — partner has already played. Key question: does the 4th player (opponent) still 
   have cards that beat us? Check `remaining_high_cards`:
   - If remaining_high_cards is empty → we can win safely with minimum winner
   - If remaining_high_cards has cards above our best → HEDGE (don't waste our best)
   - If trick_points are high → COVER anyway (worth the risk)
3. **2nd seat** — most complex. Partner AND one opponent still to play:
   - If we have the master (no remaining_high_cards above us) → COMMIT
   - If trick_points >= 15 → COMMIT (too much value to risk)
   - Otherwise → DUCK (let partner handle it, preserve our strong cards)
4. **rank_index helper** — use the mode-specific rank order to compare cards:
   - SUN: 7,8,9,J,Q,K,10,A (index 0-7)
   - HOKUM: 7,8,Q,K,10,A,9,J (index 0-7)
5. **Point feeding** — when partner is winning:
   - Find all cards we can play that DON'T overtake partner
   - Among those, pick the one with the highest point value (A=11 > 10=10 > K=4...)
   - If ALL our cards overtake partner → play the lowest overtaker (reluctant overtake)

### Constraints
- Pure functions only — no classes, no external imports beyond `__future__` and stdlib
- Use `from __future__ import annotations`
- Include docstrings on all public functions
- ~100-140 lines total
- Handle: empty legal_indices, seat values outside 2-4, empty remaining_high_cards gracefully
- Return `None` for low-confidence situations (let caller decide)
- Constants: `ORDER_SUN = ["7","8","9","J","Q","K","10","A"]`, `ORDER_HOKUM = ["7","8","Q","K","10","A","9","J"]`
- Point maps: `PTS_SUN = {"A":11,"10":10,"K":4,"Q":3,"J":2}`, `PTS_HOKUM = {"J":20,"9":14,"A":11,"10":10,"K":4,"Q":3}`
