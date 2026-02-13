Write a single self-contained Python module: `kaboot_pursuit.py`

This is a Kaboot (sweep) Pursuit Engine for a Baloot card game AI.
Kaboot means winning ALL 8 tricks in a round — it awards 44 bonus points
in Sun and doubles the round score. This module decides HOW to play
for Kaboot: card order, when to abort, and lock-in detection.

Return ONLY the Python code, no explanation.

## Function Signature

```python
def pursue_kaboot(
    hand: list,              # Card objects with .rank, .suit
    mode: str,               # "SUN" or "HOKUM"
    trump_suit: str | None,  # None for SUN
    tricks_won_by_us: int,   # consecutive wins by our team so far
    tricks_played: int,      # total tricks played this round (0-7)
    master_cards: list[int], # indices of master cards in hand
    partner_is_leading: bool, # True if partner leads the next trick
) -> dict:
    # Returns:
    # {
    #   "status": "PURSUING" | "LOCKED" | "ABORT",
    #   "play_index": int | None,     # best card index to play (if we're leading)
    #   "priority": "MASTER_FIRST" | "LONG_SUIT" | "TRUMP_DRAW" | None,
    #   "abort_reason": str | None,
    #   "reasoning": str,
    # }
```

## Constants

```python
ORDER_SUN = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]
```

## Phase Logic

| Phase | tricks_played | Strategy |
|-------|--------------|----------|
| Early (0-2) | 0-2 | Cash masters immediately to establish dominance |
| Mid (3-5) | 3-5 | If still sweeping, clear weakest suits |
| Late (6-7) | 6-7 | LOCKED — play any winner, sweep is near-guaranteed |

## Abort Conditions (set status = "ABORT")
- `tricks_won_by_us < tricks_played` → already lost a trick, no Kaboot possible
- `len(master_cards) == 0` AND `tricks_played < 5` → can't sustain the sweep
- HOKUM: no trumps left AND enemy likely has trumps → abort
- `partner_is_leading` AND `tricks_played >= 3` → trust partner, return play_index=None

## Priority Selection
- Multiple masters in hand → MASTER_FIRST (cash guaranteed wins)
- One master + long suit (≥3 cards same suit) → LONG_SUIT (run it to exhaust opponents)
- HOKUM + high trumps (J or 9) + enemy has trumps → TRUMP_DRAW (clear enemy trumps first)

## play_index Selection (when leading)
- MASTER_FIRST → pick master in shortest side suit (cash + get void)
- LONG_SUIT → lead from longest suit (pick highest rank card)
- TRUMP_DRAW → lead highest trump
- LOCKED → lead any master; if no master, lead highest-rank card

## Requirements
- Pure function, no imports beyond stdlib
- Include module docstring
- Hand cards have `.rank` and `.suit` attributes
- If partner_is_leading, set play_index = None (we're not choosing)
- Always set reasoning with a human-readable explanation
