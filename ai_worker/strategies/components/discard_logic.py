"""Discard strategy for Baloot AI when void in the led suit.

When a player cannot follow suit they must choose which card to shed.
This module encodes the strategic hierarchy: ruff in HOKUM when it pays,
feed points to a winning partner, create future voids, or shed safely.

Empirical calibration from 109 professional games (32,449 plays):
- When void, pros discard from their shortest suit 78.5% of the time
- When discarding, pros play their highest card in that suit 66.3% of the time
- Void discard distribution: 47.1% low (7/8/9), 25.9% high (A/10/K), 27.0% mid (Q/J)
"""
from __future__ import annotations
from collections import Counter
from ai_worker.strategies.components.pro_data import (
    DISCARD_SHORTEST_SUIT_RELIABILITY,
    DISCARD_HIGHEST_IN_SUIT_RELIABILITY,
    VOID_DISCARD_LOW_PCT,
    VOID_DISCARD_HIGH_PCT,
)

POINT_VALUES_SUN: dict[str, int] = {
    "A": 11, "10": 10, "K": 4, "Q": 3, "J": 2,
    "9": 0, "8": 0, "7": 0,
}
POINT_VALUES_HOKUM: dict[str, int] = {
    "J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3,
    "8": 0, "7": 0,
}

# Empirical discard rank weights: how much to prefer discarding each rank group
# Based on pro void discard distribution (47.1% low, 27.0% mid, 25.9% high)
_DISCARD_RANK_WEIGHT: dict[str, float] = {
    "7": 1.0, "8": 1.0, "9": 0.95,       # Low: 47.1% — pros strongly prefer
    "Q": 0.60, "J": 0.60,                  # Mid: 27.0% — moderate preference
    "K": 0.40, "10": 0.30, "A": 0.20,     # High: 25.9% — avoid discarding honors
}


def _pts(rank: str, mode: str) -> int:
    return (POINT_VALUES_HOKUM if mode == "HOKUM" else POINT_VALUES_SUN)[rank]


def _discard_score(card, mode: str, suit_length: int, total_suits: int) -> float:
    """Score a card for discard suitability (higher = better to discard).

    Combines:
    - Point value (low points = better to discard)
    - Empirical rank preference from pro data
    - Suit length preference: shortest suit preferred (78.5% reliability)
    """
    pts = _pts(card.rank, mode)
    rank_pref = _DISCARD_RANK_WEIGHT.get(card.rank, 0.5)

    # Shortest-suit bonus: pros pick from shortest suit 78.5% of the time
    # Scale inversely with suit length — 1 card = strongest preference
    if total_suits > 1:
        short_bonus = DISCARD_SHORTEST_SUIT_RELIABILITY * (1.0 / max(suit_length, 1))
    else:
        short_bonus = 0.0

    # Combine: rank preference is primary, shortest-suit is secondary
    # Negate point value so low-value cards score higher
    return rank_pref * 10.0 + short_bonus * 5.0 - pts * 0.3


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

    Empirical insight: pros discard from shortest suit 78.5% of the time,
    choosing the highest card within that suit 66.3% of the time.
    """
    cards = [(i, hand[i]) for i in legal_indices]
    trumps = [(i, c) for i, c in cards if mode == "HOKUM" and trump_suit and c.suit == trump_suit]
    non_trumps = [(i, c) for i, c in cards if not (mode == "HOKUM" and trump_suit and c.suit == trump_suit)]

    # --- 1. HOKUM RUFF ---------------------------------------------------
    if trumps and mode == "HOKUM":
        if not partner_winning:
            return min(trumps, key=lambda t: _pts(t[1].rank, mode))[0]
        # Partner winning → don't ruff regardless of trick_points
        # Fall through to non-trump discard logic below

    # Use non-trumps for discarding; fall back to all legal if none exist
    pool = non_trumps if non_trumps else cards

    # --- 2. POINT SHEDDING (partner winning) -----------------------------
    if partner_winning:
        # Pro insight: when partner winning, feed highest-value card (66.3% reliability)
        return max(pool, key=lambda t: _pts(t[1].rank, mode))[0]

    # --- 3. VOID CREATION (HOKUM, not ruffing) ---------------------------
    # Empirical: pros create voids from shortest suit 78.5% of the time
    if mode == "HOKUM" and trump_suit and len(pool) > 1:
        suit_counts: Counter[str] = Counter()
        for _, c in pool:
            suit_counts[c.suit] += 1
        min_len = min(suit_counts.values())
        shortest = {s for s, n in suit_counts.items() if n == min_len}
        void_candidates = [(i, c) for i, c in pool if c.suit in shortest]
        if void_candidates:
            # Within shortest suit, prefer lowest-value card (inverse of 66.3% rule:
            # when CREATING voids we shed low first; when SIGNALING we shed high)
            return min(void_candidates, key=lambda t: _pts(t[1].rank, mode))[0]

    # --- 4. EMPIRICAL DISCARD SCORING ------------------------------------
    # Use combined pro-data scoring: rank preference + shortest suit bias
    if len(pool) > 1:
        suit_counts = Counter(c.suit for _, c in pool)
        total_suits = len(suit_counts)
        scored = [
            (i, c, _discard_score(c, mode, suit_counts[c.suit], total_suits))
            for i, c in pool
        ]
        # Highest discard score = best card to throw away
        best = max(scored, key=lambda t: t[2])
        return best[0]

    # --- 5. SAFE DISCARD FALLBACK ----------------------------------------
    suit_counts = Counter(c.suit for _, c in pool)
    max_len = max(suit_counts.values())
    longest = {s for s, n in suit_counts.items() if n == max_len}
    safe = [(i, c) for i, c in pool if c.suit in longest]
    return min(safe, key=lambda t: _pts(t[1].rank, mode))[0]
