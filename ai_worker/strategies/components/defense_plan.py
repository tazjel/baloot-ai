"""Defensive strategy planner for Baloot AI.

When the opposing team wins the bid, defenders need coordinated play.
Evaluates hand strength and game state to select KABOOT_BREAK (desperate),
ACTIVE (attack with strength), or PASSIVE (conserve and react).
"""
from __future__ import annotations
from collections import defaultdict

ORDER_SUN = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]


def _suit_str(ranks: set[str], mode: str) -> float:
    """Score a suit's defensive potential from its rank set."""
    s = 0.0
    if "A" in ranks: s += 2.0 + (1.0 if "K" in ranks else 0) + (0.5 if "10" in ranks else 0)
    elif "K" in ranks: s += 0.5
    if mode == "HOKUM" and "J" in ranks: s += 2.5 + (1.5 if "9" in ranks else 0)
    return s


def plan_defense(
    my_hand: list, mode: str, trump_suit: str | None = None,
    buyer_position: str = "", partner_position: str = "",
    tricks_played: int = 0, tricks_won_by_us: int = 0,
    tricks_won_by_them: int = 0, void_suits: list[str] | None = None,
) -> dict:
    """Produce a defensive action plan for the current hand state.

    Returns strategy label, priority/avoid suits, indices to hold, and reasoning.
    """
    voids = set(void_suits or [])
    order = ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN
    # Group hand by suit → {suit: [(hand_idx, rank), ...]} sorted high→low
    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for i, c in enumerate(my_hand):
        groups[c.suit].append((i, c.rank))
    for s in groups:
        groups[s].sort(key=lambda t: order.index(t[1]), reverse=True)

    ss = {s: _suit_str({r for _, r in ranks}, mode) for s, ranks in groups.items()}
    ace_n = sum(1 for c in my_hand if c.rank == "A")
    has_ak = any({"A", "K"} <= {r for _, r in rks} for rks in groups.values())
    total = sum(ss.values())
    trump_ranks = {r for _, r in groups.get(trump_suit or "", [])}
    has_j9_trump = mode == "HOKUM" and {"J", "9"} <= trump_ranks
    notes: list[str] = []

    # --- Strategy selection ---
    if tricks_won_by_us == 0 and tricks_played >= 3:
        strat = "KABOOT_BREAK"
        notes.append(f"0/{tricks_played} tricks→break Kaboot")
    elif ace_n >= 2 or (has_ak and total >= 3.0) or has_j9_trump:
        strat = "ACTIVE"; notes.append(f"{ace_n}A str={total:.1f}→attack")
    else:
        strat = "PASSIVE"; notes.append(f"{ace_n}A str={total:.1f}→conserve")

    # --- Priority suit ---
    non_trump = {s: v for s, v in ss.items() if s != trump_suit}
    if strat == "KABOOT_BREAK":
        pri = max(ss, key=ss.get) if ss else None
    else:
        pri = max(non_trump, key=non_trump.get) if non_trump else (max(ss, key=ss.get) if ss else None)

    # --- Avoid suit ---
    if mode == "HOKUM" and trump_suit:
        if {"J", "9"} <= trump_ranks:
            avoid = min(non_trump, key=non_trump.get) if non_trump else None
            notes.append("hold J+9 trump→may attack")
        else:
            avoid = trump_suit; notes.append("avoid trump lead")
        for vs in voids:
            if vs in non_trump and vs != pri:
                avoid = vs; notes.append(f"buyer void {vs}→skip"); break
    else:
        avoid = min(non_trump, key=non_trump.get) if non_trump else None

    # --- Hold cards ---
    hold: list[int] = []
    if strat == "PASSIVE" and my_hand:
        hold.append(max(range(len(my_hand)), key=lambda i: order.index(my_hand[i].rank)))
        notes.append(f"save {my_hand[hold[0]].rank}{my_hand[hold[0]].suit}")
    elif strat == "ACTIVE":
        for idx, r in groups.get(trump_suit or "", []):
            if r in {"A", "K", "J", "9"}: hold.append(idx)

    return {"strategy": strat, "priority_suit": pri, "avoid_suit": avoid,
            "hold_cards": hold, "reasoning": f"{strat}: {'; '.join(notes)}"}
