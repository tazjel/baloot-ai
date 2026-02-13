"""Discard strategy for Baloot AI when void in the led suit.

When a player cannot follow suit they must choose which card to shed.
This module encodes the strategic hierarchy: ruff in HOKUM when it pays,
feed points to a winning partner, create future voids, or shed safely.
"""
from __future__ import annotations
from collections import Counter

POINT_VALUES_SUN: dict[str, int] = {
    "A": 11, "10": 10, "K": 4, "Q": 3, "J": 2,
    "9": 0, "8": 0, "7": 0,
}
POINT_VALUES_HOKUM: dict[str, int] = {
    "J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3,
    "8": 0, "7": 0,
}


def _pts(rank: str, mode: str) -> int:
    return (POINT_VALUES_HOKUM if mode == "HOKUM" else POINT_VALUES_SUN)[rank]


def choose_discard(
    hand: list,
    legal_indices: list[int],
    table_cards: list[dict],
    mode: str,
    trump_suit: str | None,
    partner_winning: bool,
    trick_points: int,
    cards_remaining: int,
) -> int:
    """Pick the best card index to discard when void in the led suit.

    Applies a strict priority cascade: HOKUM ruff → point shedding to
    partner → void creation → safe low-value discard.
    """
    cards = [(i, hand[i]) for i in legal_indices]
    trumps = [(i, c) for i, c in cards if mode == "HOKUM" and trump_suit and c.suit == trump_suit]
    non_trumps = [(i, c) for i, c in cards if not (mode == "HOKUM" and trump_suit and c.suit == trump_suit)]

    # --- 1. HOKUM RUFF ---------------------------------------------------
    if trumps and mode == "HOKUM":
        if not partner_winning:
            return min(trumps, key=lambda t: _pts(t[1].rank, mode))[0]
        # Partner winning → don't ruff regardless of trick_points
        # (≥10: let partner have it; <10: not worth wasting a trump)
        # Fall through to non-trump discard logic below

    # Use non-trumps for discarding; fall back to all legal if none exist
    pool = non_trumps if non_trumps else cards

    # --- 2. POINT SHEDDING (partner winning) -----------------------------
    if partner_winning:
        return max(pool, key=lambda t: _pts(t[1].rank, mode))[0]

    # --- 3. VOID CREATION (HOKUM, not ruffing) ---------------------------
    if mode == "HOKUM" and trump_suit and len(pool) > 1:
        suit_counts: Counter[str] = Counter()
        for _, c in pool:
            suit_counts[c.suit] += 1
        min_len = min(suit_counts.values())
        shortest = {s for s, n in suit_counts.items() if n == min_len}
        void_candidates = [(i, c) for i, c in pool if c.suit in shortest]
        if void_candidates:
            return min(void_candidates, key=lambda t: _pts(t[1].rank, mode))[0]

    # --- 4. SAFE DISCARD (lowest-value from longest suit) ----------------
    suit_counts = Counter(c.suit for _, c in pool)
    max_len = max(suit_counts.values())
    longest = {s for s, n in suit_counts.items() if n == max_len}
    safe = [(i, c) for i, c in pool if c.suit in longest]
    return min(safe, key=lambda t: _pts(t[1].rank, mode))[0]
