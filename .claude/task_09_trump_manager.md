Write a single self-contained Python module: `trump_manager.py`

This is a Trump Management Engine for a Baloot card game AI (HOKUM mode only).
It decides when to DRAW enemy trumps, PRESERVE ours, or set up CROSS-RUFF plays.

Return ONLY the Python code, no explanation.

## Function Signature

```python
def manage_trumps(
    hand: list,                    # Card objects with .rank, .suit
    trump_suit: str,               # e.g. "♠"
    my_trumps: int,                # count of trumps in hand
    enemy_trumps_estimate: int,    # from card tracking / void inference
    partner_trumps_estimate: int,  # from partner inference module
    tricks_played: int,            # 0-7
    we_are_buyers: bool,           # did our team win the bid?
    partner_void_suits: list[str], # suits partner is void in
    enemy_void_suits: list[str],   # suits enemies are void in
) -> dict:
    # Returns:
    # {
    #   "action": "DRAW" | "PRESERVE" | "CROSS_RUFF" | "NEUTRAL",
    #   "lead_trump": bool,          # should we lead trump now?
    #   "safe_side_suits": [str],    # suits safe to lead (no enemy ruff)
    #   "ruff_target_suits": [str],  # suits where WE can ruff
    #   "reasoning": str
    # }
```

## Constants

```python
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]
ALL_SUITS = ["♠", "♥", "♦", "♣"]
```

## Logic Rules

| Condition | Action | Why |
|-----------|--------|-----|
| J+9 in hand, enemy has trumps | DRAW | Extract their trumps with dominant position |
| ≤2 trumps, enemy has more | PRESERVE | Save for defensive ruffs |
| Partner void in X, we have trump | CROSS_RUFF | Lead X so partner ruffs, partner leads Y for us |
| Enemy void in suit X + has trump | Mark X as unsafe | They'll ruff our lead |
| All enemy trumps drawn | NEUTRAL | Cash side winners freely |
| Late game (≥5 tricks), 1 trump left | PRESERVE | Save last trump for critical ruff |
| We are buyers + J or 9 + ≥3 trumps | DRAW | Offensive trump extraction |
| We are defenders + ≤2 trumps | PRESERVE | Never waste trump on defense |

## Requirements
- Pure function, no imports beyond stdlib (collections OK)
- Include module docstring
- Hand cards have `.rank` and `.suit` attributes
- `safe_side_suits` = all non-trump suits minus enemy void suits
- `ruff_target_suits` = suits where WE are void but have trumps to ruff with
