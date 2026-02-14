"""Hand shape evaluator for Baloot AI.

Analyses distribution pattern (e.g. 5-3-1-0) and returns bid adjustments
for both SUN and HOKUM modes.  Covers ruff potential, long-suit running
tricks, and shape classification from BALANCED to EXTREME.
"""
from __future__ import annotations
from collections import Counter

from ai_worker.strategies.constants import ALL_SUITS, ORDER_SUN, ORDER_HOKUM

# ── 8-CARD DISTRIBUTIONS (Baloot deals 8 cards across 4 suits) ──
# (sorted pattern tuple) → (type, sun_adj, hokum_adj)
# Patterns must sum to 8. Each card in a 32-card deck appears once.
_SHAPES: dict[tuple, tuple[str, float, float]] = {
    # === BALANCED (all suits represented, max 3 in any suit) ===
    (2, 2, 2, 2):  ("BALANCED",       2,  -3),  # Perfect balance = ideal SUN
    (3, 2, 2, 1):  ("SEMI_BALANCED",  1,  -1),  # Slight imbalance, still OK for SUN

    # === SEMI-BALANCED (one suit starts to dominate) ===
    (3, 3, 1, 1):  ("SEMI_BALANCED",  0,   1),  # Two 3-card suits, two singletons
    (3, 3, 2, 0):  ("SEMI_BALANCED", -1,   2),  # Void + two 3s = HOKUM-leaning
    (4, 2, 1, 1):  ("SEMI_BALANCED", -1,   2),  # 4-card suit = potential trump base

    # === UNBALANCED (strong suit concentration) ===
    (4, 2, 2, 0):  ("UNBALANCED",    -2,   3),  # 4-card trump + void = strong HOKUM
    (4, 3, 1, 0):  ("UNBALANCED",    -2,   4),  # 4-trump + 3-side + void = excellent
    (4, 4, 0, 0):  ("UNBALANCED",    -3,   4),  # Two 4-card suits, two voids = extreme
    (5, 2, 1, 0):  ("UNBALANCED",    -3,   5),  # 5-card trump + void = HOKUM dream
    (5, 1, 1, 1):  ("UNBALANCED",    -3,   4),  # 5-card trump, all singletons
    (5, 2, 0, 0) : ("UNBALANCED",    -4,   5),  # 5+2, two voids (unlikely but valid with 8 cards from 32)

    # === EXTREME (dominant single suit) ===
    (5, 3, 0, 0):  ("EXTREME",       -4,   6),  # 5+3, two voids = monster HOKUM shape
    (6, 1, 1, 0):  ("EXTREME",       -5,   6),  # 6-card suit = near auto-bid HOKUM
    (6, 2, 0, 0):  ("EXTREME",       -5,   7),  # 6+2, two voids
    (6, 1, 0, 0):  ("EXTREME",       -5,   7),  # 6+1, two voids (7 non-trump cards used)
    (7, 1, 0, 0):  ("EXTREME",       -6,   8),  # 7 trumps! Nearly impossible to lose HOKUM
    (8, 0, 0, 0):  ("EXTREME",       -6,   8),  # All 8 cards in one suit
}


def _classify(pattern: tuple[int, ...]) -> tuple[str, float, float]:
    """Classify sorted pattern → (shape_type, sun_adj, hokum_adj).

    First checks the 8-card distribution lookup table; if the pattern isn't
    found (e.g. mid-round with fewer cards), uses heuristic fallback.
    """
    if pattern in _SHAPES:
        return _SHAPES[pattern]

    # Heuristic fallback for mid-round patterns (fewer than 8 cards)
    longest = pattern[0] if pattern else 0
    has_void = 0 in pattern
    void_count = sum(1 for x in pattern if x == 0)

    if longest >= 6:
        extra = min(longest - 5, 2)
        return ("EXTREME", -5, 5 + extra)
    if void_count >= 2:
        return ("EXTREME", -4, 5)
    if has_void:
        return ("UNBALANCED", -3, 4)
    if longest >= 4:
        return ("SEMI_BALANCED", -1, 2)
    if longest >= 3:
        return ("SEMI_BALANCED", 0, 1)
    return ("BALANCED", 1, -2)


def _long_tricks(hand: list, suit_cards: dict[str, list], mode: str) -> float:
    """Estimate extra tricks from long suits.

    Calibrated for 8-card Baloot hands where 3+ in a suit is already
    significant and 4+ is dominant. Each suit has 8 cards total in deck
    (7,8,9,10,J,Q,K,A), so holding 4+ means opponents share ≤4.
    """
    total = 0.0
    for suit, cards in suit_cards.items():
        n = len(cards)
        ranks = {c.rank for c in cards}
        has_a, has_k, has_10 = "A" in ranks, "K" in ranks, "10" in ranks
        if n >= 6 and has_a:
            total += 3.0  # 6+ with Ace = likely runs the whole suit
        elif n >= 5 and has_a:
            total += 2.0  # 5 with Ace = opponents have only 3
        elif n >= 4 and has_a and has_k:
            total += 1.5  # A-K + 2 more = strong running suit
        elif n >= 4 and has_a:
            total += 1.0  # 4 with Ace = good length
        elif n >= 4 and has_k and has_10:
            total += 0.5  # K-10 with length = can establish
        elif n >= 3 and has_a and has_k and has_10:
            total += 0.5  # A-K-10 tight = runs well despite shorter length
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
