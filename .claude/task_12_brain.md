Write a single self-contained Python module: `brain.py`

This is the Cross-Module Integration Layer ("Brain") for a Baloot card game AI.
It orchestrates multiple AI modules and reconciles conflicting advice
using a priority cascade. When modules disagree, the higher-priority one wins.

Return ONLY the Python code, no explanation.

## Function Signature

```python
def consult_brain(
    hand: list,               # Card objects with .rank, .suit
    table_cards: list[dict],  # [{"rank":"A","suit":"♠","playedBy":"Bottom"}, ...]
    mode: str,                # "SUN" or "HOKUM"
    trump_suit: str | None,
    position: str,            # "Bottom", "Right", "Top", "Left"
    we_are_buyers: bool,
    partner_winning: bool,
    tricks_played: int,
    tricks_won_by_us: int,
    master_indices: list[int],  # indices of master cards in hand
    tracker_voids: dict[str, list[str]],  # {suit: [void_player_positions]}
    partner_info: dict | None,  # from partner inference module, may be None
) -> dict:
    # Returns:
    # {
    #   "recommendation": int | None,  # card index, or None if no strong opinion
    #   "confidence": float,           # 0.0-1.0
    #   "modules_consulted": list[str],
    #   "reasoning": str,
    # }
```

## Priority Cascade (highest → lowest)

| Priority | Module | When Active | What It Does |
|----------|--------|-------------|-------------|
| 1 | Kaboot Pursuit | `tricks_won_by_us == tricks_played` and `we_are_buyers` | Sweep strategy override |
| 2 | Point Density | `len(table_cards) >= 1` | Evaluate if trick is worth fighting |
| 3 | Trump Manager | `mode == "HOKUM"` and leading (no table_cards) | DRAW/PRESERVE/CROSS_RUFF |
| 4 | Defense Plan | `not we_are_buyers` and leading | Priority/avoid suit guidance |
| 5 | Partner Signal | `partner_info` has `likely_strong_suits` | Lead partner's strong suits |
| 6 | Default | Always | Return None, let existing heuristics decide |

## Orchestration Logic

```
For each module in priority order:
    if module's activation condition is met:
        call module
        add module name to modules_consulted
        if module returns a recommendation with confidence >= 0.5:
            set recommendation = module's answer
            set confidence = module's confidence
            break
    else:
        skip module

If no module had confidence >= 0.5:
    recommendation = None
    confidence = 0.0
```

## Module Call Stubs

Since you CAN'T import the other modules (they may not exist yet),
use these **inline micro-implementations** inside consult_brain:

### Kaboot Check (inline)
```python
# If we've won every trick so far and we're the buyers
pursuing = (tricks_won_by_us == tricks_played and tricks_played > 0 and we_are_buyers)
if pursuing and master_indices:
    recommendation = master_indices[0]  # play first master
    confidence = 0.9
```

### Point Density Check (inline)
```python
POINT_VALUES_SUN = {"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2}
POINT_VALUES_HOKUM = {"J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3}
pv = POINT_VALUES_HOKUM if mode == "HOKUM" else POINT_VALUES_SUN
pts = sum(pv.get(tc.get("rank", ""), 0) for tc in table_cards)
# If CRITICAL (26+) and we can win → play highest
# If EMPTY and partner winning → don't override
```

### Trump Manager Check (inline, HOKUM only)
```python
my_trumps = [i for i, c in enumerate(hand) if c.suit == trump_suit]
trump_ranks = {hand[i].rank for i in my_trumps}
has_j9 = {"J", "9"} <= trump_ranks
# If has_j9 and enemies have trumps → lead trump (DRAW)
# If ≤1 trump → don't lead trump (PRESERVE)
```

### Defense Check (inline)
```python
# If defending, prefer leading from strongest non-trump suit
# Avoid suits where opponents are void (they'll ruff)
```

### Partner Signal Check (inline)
```python
if partner_info and partner_info.get("likely_strong_suits"):
    target = partner_info["likely_strong_suits"][0]
    candidates = [i for i, c in enumerate(hand) if c.suit == target]
    if candidates:
        recommendation = candidates[0]
        confidence = partner_info.get("confidence", 0.3) * 0.8
```

## Requirements
- Pure function, no external imports (all logic inline)
- Include module docstring explaining the priority cascade
- Always populate modules_consulted with which checks ran
- reasoning should say which module won and why
- If multiple modules agree, boost confidence by 0.1
- Return None recommendation if no module is confident enough
- Handle all edge cases (empty hand, no table cards, None partner_info)
