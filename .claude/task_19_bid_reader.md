# Task 19: Bid Reader — `bid_reader.py`

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

## How Baloot Bidding Works

Bidding has **two rounds**. In each round, players go clockwise starting from the dealer's right.

**Round 1 (HOKUM only):**
- Each player can bid "HOKUM" in a SPECIFIC suit (the suit of the face-up card) or "PASS"
- The face-up card's suit becomes trump if someone bids HOKUM
- A HOKUM bid means "I believe my team can win with this trump suit"

**Round 2 (SUN or HOKUM in a different suit):**
- If everyone passed in round 1, round 2 begins
- Players can bid "SUN" (no trump — strong balanced hand) or "HOKUM" in ANY suit EXCEPT the round-1 suit
- Or they can "PASS" again

**Doubling (الدبل):** After a bid is accepted, the opposing team can "DOUBLE" (challenge the bid). The bidding team can then "RE-DOUBLE" (counter-challenge).

## What Already Exists (DO NOT duplicate)

We have `partner_read.py` that analyzes partner's bids and trick play for partnership coordination:
```python
def read_partner(partner_position, bid_history, trick_history, mode, trump_suit) -> dict:
    # Returns partner's strong/void suits, estimated trumps, confidence
```

We also have `opponent_model.py` that tracks opponents during TRICK PLAY (cards they play, voids, etc.):
```python
def model_opponents(my_position, bid_history, trick_history, mode, trump_suit) -> dict:
    # Returns per-opponent profiles focused on trick behavior
```

**Key gap:** Nobody deeply analyzes OPPONENT BIDS for play-phase intelligence. The opponent_model looks at bids briefly (+3 for HOKUM bid, -0.3 for PASS) but doesn't extract the rich information hiding in the bidding sequence.

## Actual Data Shapes

**bid_history** looks like:
```python
[
    {"player": "Bottom", "action": "PASS"},
    {"player": "Right", "action": "HOKUM", "suit": "♥"},
    {"player": "Top", "action": "PASS"},
    {"player": "Left", "action": "PASS"},
    # Round 2 bids may follow if round 1 was all passes:
    # {"player": "Bottom", "action": "SUN"},
    # or {"player": "Bottom", "action": "HOKUM", "suit": "♠"},
]
```

**game_score** — current game score for context:
```python
{"us": 120, "them": 85}  # points accumulated across rounds
```

## Your Task
Create **`bid_reader.py`** — extracts play-phase intelligence from the bidding history.

### Required Function
```python
def read_bids(
    bid_history: list[dict],       # bidding sequence as shown above
    my_position: str,              # "Bottom", "Right", "Top", "Left"
    mode: str,                     # "SUN" or "HOKUM" (the resolved mode)
    trump_suit: str | None,        # resolved trump suit, None if SUN
) -> dict:
```

### Return Format
```python
{
    "buyer": {
        "position": "Right",
        "strength": "STRONG",          # "STRONG" | "MARGINAL" | "OVERBID"
        "likely_strong_suits": ["♥"],  # suits they likely hold strength in
        "bid_round": 1,                # which round they bid in (1 or 2)
    },
    "passer_insights": {
        "Bottom": {
            "weak_suits": ["♥"],       # face-up suit they refused
            "passed_round": 1,         # which round(s) they passed
        },
        "Top": { ... },
        "Left": { ... },
    },
    "play_implications": {
        "safe_leads": ["♦", "♣"],      # suits the buyer is likely WEAK in
        "avoid_leads": ["♥"],          # suits the buyer is likely STRONG in
        "partner_likely_has": ["♠"],   # inferred from partner's bid behavior
    },
    "was_doubled": False,              # did opposing team double
    "was_redoubled": False,            # did bidding team re-double
    "reasoning": "Right bid HOKUM ♥ in R1 (strong trumps). All others passed ♥ = weak in ♥."
}
```

### Logic to Implement

1. **Find the buyer** — scan bid_history for the accepted bid (HOKUM or SUN action).
   The buyer is the player whose bid was NOT followed by another bid.

2. **Buyer strength assessment:**
   - **R1 HOKUM bid** → STRONG (they saw a specific suit and committed immediately)
   - **R2 HOKUM bid** → MARGINAL (they passed in R1, only bid when forced/desperate)
   - **R2 SUN bid** → check if they passed R1. If yes → MARGINAL (couldn't find a trump suit).
     If they bid SUN directly → could be STRONG (balanced hand)
   - **If doubled** → either opponent team is confident, OR it's a bluff. Mark `was_doubled=True`.
   - **If re-doubled** → bidding team is extremely confident. Upgrade strength.

3. **Passer insights** — for each player who passed:
   - R1 pass on HOKUM → they are WEAK in the face-up suit (the suit they could have bid)
   - R2 pass on everything → they have a genuinely weak hand overall
   - Even our PARTNER's passes are informative: if partner passed ♥ in R1, 
     don't expect partner help in ♥

4. **Play implications — the key output:**
   - `safe_leads`: suits NOT mentioned in any bid, suits passers showed weakness in
   - `avoid_leads`: the trump suit (in HOKUM), suits the buyer likely controls
   - `partner_likely_has`: if partner bid and lost → they showed strength in that suit.
     If partner passed everything → weaker hand overall.

5. **Buyer's likely strong suits:**
   - HOKUM buyer → strong in trump suit + possibly one side suit
   - SUN buyer → probably strong across multiple suits (balanced)
   - If buyer bid in R2 after passing R1 → they avoided the R1 suit, so they're 
     strong in something ELSE

### Edge Cases
- If bid_history is empty → return neutral defaults
- If no buyer found (all passes — shouldn't happen but handle it) → return safe defaults
- Treat "DOUBLE" / "REDOUBLE" as special actions (not bids for a mode)
- The face-up suit for R1 can be inferred: it's the suit of the first HOKUM bid if any,
  or the suit that was available for R1 bidding. If no one bid HOKUM in R1, 
  the face-up suit info may not be in bid_history — handle gracefully.

### Constraints
- Pure functions only — no classes, no external imports beyond `__future__` and stdlib
- Use `from __future__ import annotations`
- Include docstrings on all public functions
- ~90-130 lines total
- Handle: empty bid_history, missing fields, unknown positions gracefully
- Constants: `POSITIONS = ["Bottom", "Right", "Top", "Left"]`, `ALL_SUITS = ["♠","♥","♦","♣"]`
