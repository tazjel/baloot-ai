# Task 20: Mid-Game Planner — `mid_game_planner.py`

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

## The Problem This Solves

The bot currently has two levels of play intelligence:

1. **Endgame solver** (`endgame_solver.py`) — at ≤3 cards per player, runs perfect minimax with alpha-beta pruning. Provably optimal.
2. **Heuristic scoring** — at 4-8 cards, each card is scored independently (master bonus, suit length, void penalties) and the highest score wins. No lookahead.

**The gap:** At 4-6 cards remaining, the game tree is small enough to plan 2-3 tricks ahead, but the bot treats each card in isolation. It can't think "if I play this master now, I can exit to partner next trick, and they'll cash their master."

## What Already Exists (DO NOT duplicate)

**endgame_solver.py** — handles ≤3 cards with minimax:
```python
def solve_endgame(my_hand, known_hands, my_position, leader_position, mode, trump_suit) -> dict:
    # Returns {cardIndex, expected_points, reasoning}
    # Only works when ALL hands are known and ≤3 cards each
```

**brain.py** — the orchestrator that calls various modules:
```python
def consult_brain(ctx, brain_modules) -> dict | None:
    # Calls endgame solver, card tracker, etc. in cascade
    # Gap: no module handles the 4-6 card range with planning
```

**card_tracker.py** — tracks remaining cards:
```python
tracker.get_remaining_in_suit(suit) -> list[dict]  # returns [{rank, suit}, ...]
tracker.is_my_card_master(card, mode) -> bool
```

## Your Task
Create **`mid_game_planner.py`** — a multi-trick planning engine for when 4-6 cards remain.

### Required Function
```python
def plan_sequence(
    hand: list,                        # card objects with .rank, .suit
    mode: str,                         # "SUN" or "HOKUM"
    trump_suit: str | None,            # trump suit if HOKUM, None if SUN
    tricks_remaining: int,             # how many tricks left (should be 4-6)
    master_indices: list[int],         # indices of cards that are currently master
    our_tricks: int,                   # tricks our team has won this round
    their_tricks: int,                 # tricks opponents have won this round
    remaining_cards_by_suit: dict[str, list[str]],  # {suit: [rank, rank, ...]} of unplayed cards
) -> dict | None:
```

### Return Format
```python
{
    "card_index": 1,                   # index into hand — the card to play NOW
    "plan": "CASH_AND_EXIT",           # one of the plans below
    "confidence": 0.75,                # 0.0-1.0
    "reasoning": "Cash A♠ (master) now, then exit via 7♦ to partner. 2 tricks planned.",
    "expected_tricks": 2,              # how many tricks this plan expects to win
}
```
Return `None` if:
- tricks_remaining is outside 4-6 range
- hand is empty
- No clear plan emerges (confidence would be < 0.5)

### Plans to Implement

1. **CASH_AND_EXIT** — Play all masters first, then lead a low card to transfer lead to partner.
   - **Detection:** We hold ≥1 master AND ≥1 non-master card in a different suit
   - **Logic:** 
     - Count consecutive masters we can cash (guaranteed wins)
     - After cashing, we need an "exit card" — a low card in a suit where partner is likely strong
     - Play the master from the SHORTEST suit first (to create void for potential ruffing)
   - **Confidence:** 0.8 if we have 2+ masters, 0.65 if only 1 master
   - **expected_tricks:** number of masters we hold

2. **STRIP_THEN_ENDPLAY** — Remove one suit from play, then force opponents into an unfavorable lead.
   - **Detection:** We hold ALL remaining cards in one suit (we "control" it), 
     plus cards in other suits
   - **Logic:**
     - If we control a suit: cash the master(s) in that suit first to strip it
     - Then opponents can't lead that suit — they must lead something we can exploit
     - Good when: we hold 2 cards in suit A (both masters) + 2-4 cards in other suits
   - **Confidence:** 0.7 if we control a suit, 0.5 otherwise
   - **expected_tricks:** masters + 1 (for the endplay advantage)

3. **TRUMP_FORCE** — In HOKUM mode, lead side suits to force opponents to spend trumps.
   - **Detection:** mode == "HOKUM", we have trumps, opponents likely have trumps too
   - **Logic:**
     - Lead non-trump non-master cards to force opponents to trump
     - This depletes their trump supply, making our remaining trumps more valuable
     - Best when: we have 1-2 trumps left, opponents likely have 1-2 trumps
   - **Confidence:** 0.55 (uncertain — depends on opponent holdings)
   - **expected_tricks:** estimate 1 from forcing + trumps_remaining

4. **COUNT_AND_DUCK** — Surrender this trick intentionally to control the remaining tricks.
   - **Detection:** We're LOSING on tricks (their_tricks > our_tricks) but hold strong 
     cards for later, AND winning this trick doesn't help (opponent leads a suit where 
     our cards lose anyway)
   - **Logic:**
     - Sometimes the best play is to LOSE this trick cheaply (play lowest card)
     - This preserves our strong cards for tricks we CAN win
     - Key insight: don't waste a semi-strong card trying to win an unwinnable trick
   - **Confidence:** 0.6 if clear advantage from ducking
   - **expected_tricks:** estimate based on masters + remaining tricks

5. **DESPERATION_GAMBIT** — We're far behind on tricks and must take risks.
   - **Detection:** their_tricks >= our_tricks + 2 (losing badly)
   - **Logic:** 
     - Lead our HIGHEST card regardless of whether it's master
     - Hope for the best — at this point heuristics are better than conservative play
     - Skip if we have masters (use CASH_AND_EXIT instead)
   - **Confidence:** 0.4 (last resort)

### Selection Priority
Evaluate plans in this order and return the FIRST one with confidence >= 0.5:
1. CASH_AND_EXIT (if we have masters)
2. STRIP_THEN_ENDPLAY (if we control a suit)
3. TRUMP_FORCE (if HOKUM mode, applicable)
4. COUNT_AND_DUCK (if strategically beneficial)
5. DESPERATION_GAMBIT (if losing badly)
If none qualify → return `None`

### Logic Helpers You'll Need

```python
def _suit_groups(hand):
    """Group hand indices by suit → {suit: [(index, card), ...]}"""
    
def _count_masters(hand, master_indices):
    """Count how many masters we hold and in which suits."""

def _find_exit_card(hand, master_indices, remaining_cards_by_suit, mode):
    """Find the best card to 'exit' with (lowest card in a suit we don't control)."""

def _controls_suit(hand_in_suit, remaining_in_suit):
    """Check if our cards in a suit are ALL masters (we control the suit)."""
```

### Constraints
- Pure functions only — no classes, no external imports beyond `__future__` and stdlib
- Use `from __future__ import annotations`
- Include docstrings on all public functions
- ~120-160 lines total
- Handle: empty hand, tricks_remaining outside 4-6, empty remaining_cards_by_suit gracefully
- Return `None` for any situation where no plan has confidence >= 0.5
- This module does NOT do minimax — that's `endgame_solver.py`'s job. 
  This module does HEURISTIC multi-trick planning (pattern recognition, not tree search)
- Constants: `ORDER_SUN = ["7","8","9","J","Q","K","10","A"]`, `ORDER_HOKUM = ["7","8","Q","K","10","A","9","J"]`
- Point maps: `PTS_SUN = {"A":11,"10":10,"K":4,"Q":3,"J":2}`, `PTS_HOKUM = {"J":20,"9":14,"A":11,"10":10,"K":4,"Q":3}`
