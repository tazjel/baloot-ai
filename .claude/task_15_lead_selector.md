# Task 15: Lead Selector — `lead_selector.py`

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

We already have these modules (all pure-function, no classes):
- `partner_read.py` → `read_partner(...)` → {likely_strong_suits, likely_void_suits, estimated_trumps, confidence}
- `defense_plan.py` → `plan_defense(...)` → {strategy, priority_suit, avoid_suit, hold_cards}
- `trump_manager.py` → `manage_trumps(...)` → {strategy: DRAW/PRESERVE/CROSS_RUFF, lead_index}
- `card_tracker.py` → tracks remaining cards, master cards, void info

Currently the Sun/Hokum `_get_X_lead()` methods have 200+ lines of
inline heuristics. We need a **unified lead selector** that consults
the specialized modules and picks the best opening card.

## Your Task
Create **`lead_selector.py`** — a unified lead-card selection engine.

### Required Function
```python
def select_lead(
    hand: list,                      # card objects with .rank, .suit
    mode: str,                       # "SUN" or "HOKUM"
    trump_suit: str | None,
    we_are_buyers: bool,
    tricks_played: int,
    tricks_won_by_us: int,
    master_indices: list[int],       # indices in hand that are master cards
    partner_info: dict | None,       # from read_partner()
    defense_info: dict | None,       # from plan_defense()
    trump_info: dict | None,         # from manage_trumps()
    opponent_voids: dict[str, set],  # {suit: {positions who are void}}
) -> dict:
```

### Return Format
```python
{
    "card_index": 3,
    "strategy": "MASTER_CASH",    # one of the labels below
    "confidence": 0.85,
    "reasoning": "A♠ is master, ♠ not voided by opponents, cash guaranteed win"
}
```

### Strategy Labels
| Label | When | Description |
|-------|------|-------------|
| MASTER_CASH | Master cards available | Lead master from shortest suit for void creation |
| TRUMP_DRAW | HOKUM, have J+9 | Lead high trump to strip enemy trumps |
| PARTNER_FEED | Partner strong in a suit | Lead low in partner's strong suit |  
| LONG_RUN | 4+ cards in a suit with A | Run length once opponents void |
| SAFE_LEAD | No clear winner | Lead from longest non-trump, avoid opponent voids |
| DEFENSE_PRIORITY | Defending | Follow defense_plan's priority suit guidance |
| DESPERATION | Late game, losing | Lead highest raw card, hope for the best |

### Logic to Implement
1. **Master priority** — if we have masters, lead one from the shortest side suit
2. **Trump draw** (HOKUM) — if trump_info says DRAW and we have J+9, lead trump
3. **Partner feed** — if partner_info shows strong suit with confidence ≥ 0.4, feed it
4. **Void avoidance** — never lead a suit where opponents are void (they'll trump/discard)
5. **Long suit run** — if we have 4+ in a suit with the top card, build winners
6. **Defense mode** — if defending, follow defense_plan's priority/avoid guidance
7. **Desperation** — tricks 6-7, losing → lead highest card regardless
8. **Tie-breaking** — prefer shorter suits (void creation), then higher cards

### Constraints
- Pure functions, no classes, no external deps
- Do NOT import the other modules; accept their outputs as parameters
- Use `from __future__ import annotations`
- Include docstrings
- ~100-140 lines
- Handle edge cases: empty hand, no masters, all suits voided, None info dicts
