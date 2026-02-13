# Baloot AI — Batch Module Generation

You are generating Python modules for a Baloot AI strategy system.

## Instructions
Below are multiple task specifications separated by `---TASK---` markers. For EACH task:
1. Read the specification carefully
2. Write the complete Python module
3. Create it as a **downloadable Python file artifact** (`.py` file)

**IMPORTANT:** Create each module as a separate `.py` file artifact — NOT as code blocks in chat.
Name each artifact exactly as specified in the task (e.g. `opponent_model.py`).

Process ALL tasks below. Do NOT stop after one. If you hit your limit, finish the current module completely before stopping. If you stop, I will say "continue" and you should pick up with the next task.

---

## GLOBAL CONTEXT (applies to ALL tasks)

**Game:** Baloot — Saudi Arabian trick-taking card game
- 4 players in 2 teams (Bottom+Top vs Right+Left)
- 32 cards: ranks 7, 8, 9, 10, J, Q, K, A in suits ♠, ♥, ♦, ♣
- 8 tricks per round, 8 cards per player

**Card objects:** Have `.rank` (str) and `.suit` (str, one of "♠","♥","♦","♣")

**Modes & Rank Order:**
- SUN (no trump): 7 < 8 < 9 < J < Q < K < 10 < A
- HOKUM (trump suit): 7 < 8 < Q < K < 10 < A < 9 < J

**Point Values:**
- SUN: A=11, 10=10, K=4, Q=3, J=2, rest=0
- HOKUM: J=20, 9=14, A=11, 10=10, K=4, Q=3, rest=0

**Positions:** "Bottom", "Right", "Top", "Left"
**Teams:** Bottom+Top (team 0) vs Right+Left (team 1)

**trick_history format** (from game state):
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
]
```

**Global Rules for ALL modules:**
- Pure functions only — no classes
- No external imports beyond `from __future__ import annotations` and `collections`
- Include module-level docstring and function docstrings
- Handle edge cases: empty inputs, missing dict keys, None values


---TASK--- (task_13_opponent_model.md)

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

---TASK--- (task_14_hand_shape.md)

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

---TASK--- (task_15_trick_review.md)

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

---TASK--- (task_16_cooperative_play.md)

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