"""Hand shape evaluator for Baloot AI.

Analyses distribution pattern (e.g. 5-3-1-0) and returns bid adjustments
for both SUN and HOKUM modes.  Covers ruff potential, long-suit running
tricks, and shape classification from BALANCED to EXTREME.
"""
from __future__ import annotations
from collections import Counter

ALL_SUITS = ["♠", "♥", "♦", "♣"]
ORDER_SUN = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]

# (sorted pattern tuple) → (type, sun_adj, hokum_adj)
_SHAPES: dict[tuple, tuple[str, float, float]] = {
    (4, 3, 3, 3): ("BALANCED", 0, -2),
    (4, 4, 3, 2): ("BALANCED", 0, -1),
    (5, 3, 3, 2): ("SEMI_BALANCED", -1, 2),
    (4, 3, 2, 1): ("SEMI_BALANCED", -1, 2),
    (5, 4, 2, 2): ("SEMI_BALANCED", -2, 3),
    (5, 3, 1, 1): ("UNBALANCED", -3, 4),
    (5, 4, 3, 1): ("UNBALANCED", -2, 3),
}


def _classify(pattern: tuple[int, ...]) -> tuple[str, float, float]:
    """Classify sorted pattern → (shape_type, sun_adj, hokum_adj)."""
    if pattern in _SHAPES:
        return _SHAPES[pattern]
    longest = pattern[0] if pattern else 0
    has_void = 0 in pattern
    if longest >= 6:
        extra = min(longest - 5, 2)  # +4 to +6
        return ("EXTREME", -4, 4 + extra)
    if has_void:
        return ("UNBALANCED", -4, 5)
    # Fallback for unusual mid-game patterns
    if longest >= 5:
        return ("UNBALANCED", -2, 3)
    return ("BALANCED", 0, 0)


def _long_tricks(hand: list, suit_cards: dict[str, list], mode: str) -> float:
    """Estimate extra tricks from long suits."""
    order = ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN
    total = 0.0
    for suit, cards in suit_cards.items():
        n = len(cards)
        ranks = {c.rank for c in cards}
        has_a, has_k, has_10 = "A" in ranks, "K" in ranks, "10" in ranks
        if n >= 6 and has_a:
            total += 2.0
        elif n >= 5 and has_a and has_k:
            total += 1.5
        elif n >= 5 and has_a:
            total += 1.0
        elif n >= 4 and has_a and has_k and has_10:
            total += 0.5
    return total


def evaluate_shape(
    hand: list,
    mode: str,
    trump_suit: str | None = None,
) -> dict:
    """Evaluate hand distribution and return bid adjustments.

    Classifies the shape pattern, computes ruff potential (HOKUM),
    long-suit running tricks, and a combined bid_adjustment score.
    """
    suit_cards: dict[str, list] = {s: [] for s in ALL_SUITS}
    for c in hand or []:
        suit_cards[c.suit].append(c)

    lengths = {s: len(cards) for s, cards in suit_cards.items()}
    pattern = tuple(sorted(lengths.values(), reverse=True))
    label = "-".join(str(x) for x in pattern)
    voids = [s for s in ALL_SUITS if lengths[s] == 0]
    singletons = [s for s in ALL_SUITS if lengths[s] == 1]
    long_suits = [(s, lengths[s]) for s in ALL_SUITS if lengths[s] >= 4]

    shape_type, sun_adj, hokum_adj = _classify(pattern)

    # Ruff potential (HOKUM only)
    ruff = 0.0
    if mode == "HOKUM" and trump_suit:
        trump_n = lengths.get(trump_suit, 0)
        # Estimate top trump tricks (J, 9, A in trump)
        trump_ranks = {c.rank for c in suit_cards.get(trump_suit, [])}
        top_trump = sum(1 for r in ("J", "9", "A") if r in trump_ranks)
        spare = max(0, trump_n - top_trump)
        for s in ALL_SUITS:
            if s == trump_suit:
                continue
            if lengths[s] == 0:
                ruff += 1.0
            elif lengths[s] == 1:
                ruff += 0.5
        ruff = min(ruff, spare)

    long_t = _long_tricks(hand, suit_cards, mode)
    adj = hokum_adj if mode == "HOKUM" else sun_adj
    adj += ruff * 0.5 + long_t * 0.5  # modest contribution to final bid

    notes = [f"{label} {shape_type}"]
    if voids:
        notes.append(f"void {''.join(voids)}")
    if singletons:
        notes.append(f"single {''.join(singletons)}")
    if ruff:
        notes.append(f"{ruff:.1f} ruffs")
    if long_t:
        notes.append(f"{long_t:.1f} long tricks")

    return {
        "pattern": list(pattern),
        "pattern_label": label,
        "shape_type": shape_type,
        "bid_adjustment": round(adj, 1),
        "voids": voids,
        "singletons": singletons,
        "long_suits": long_suits,
        "ruff_potential": round(ruff, 1),
        "long_suit_tricks": round(long_t, 1),
        "reasoning": "; ".join(notes),
    }
