"""Trick-projection estimator for Baloot AI.

Estimates how many of the 8 tricks a hand can win by counting quick
tricks (top honours), long-suit extras, and HOKUM ruff potential.
Used by both the bidding evaluator and mid-round play strategy.
"""
from __future__ import annotations
from collections import defaultdict
from math import floor

ORDER_SUN = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]


def _suit_qt(ranks: set[str]) -> float:
    """Quick tricks for a non-trump suit: A=1, +K=0.5, +10=0.5; bare K=0.5."""
    if "A" not in ranks:
        return 0.5 if "K" in ranks else 0.0
    return 1.0 + (0.5 if "K" in ranks else 0.0) + (0.5 if {"K", "10"} <= ranks else 0.0)


def _trump_qt(ranks: list[str]) -> float:
    """Count unbroken sequence from top of HOKUM trump order (J,9,A,10,…)."""
    idxs = sorted((ORDER_HOKUM.index(r) for r in ranks), reverse=True)
    qt, expect = 0.0, 7  # J is index 7
    for v in idxs:
        if v == expect:
            qt += 1.0; expect -= 1
        else:
            break
    return qt


def project_tricks(
    hand: list, mode: str, trump_suit: str | None = None,
    void_suits: list[str] | None = None, partner_known_cards: list | None = None,
) -> dict:
    """Estimate trick-taking potential of *hand*.

    Returns min/expected/max tricks plus component breakdown of quick
    tricks, long-suit extras, and ruff potential.
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for c in hand:
        groups[c.suit].append(c.rank)
    trump_n = len(groups.get(trump_suit, [])) if trump_suit else 0
    quick = long_ = ruff = 0.0
    details: list[str] = []

    for suit in ["♠", "♥", "♦", "♣"]:
        ranks = groups.get(suit, [])
        n = len(ranks)
        # --- Void suit: ruff potential in HOKUM ---
        if n == 0:
            if mode == "HOKUM" and trump_suit and suit != trump_suit and trump_n > 0:
                ruff += 1.0; details.append(f"void {suit}→+1R")
            continue
        # --- Trump suit ---
        if mode == "HOKUM" and suit == trump_suit:
            tq = _trump_qt(ranks)
            quick += tq
            if tq: details.append(f"trump: {tq:.1f}qt")
            continue
        # --- Non-trump / SUN suit ---
        rs = set(ranks)
        sq = _suit_qt(rs)
        quick += sq
        if sq: details.append(f"{suit}: {sq:.1f}qt")
        if n >= 5 and rs & {"A", "K"}:
            lt = (n - 4) * 0.5
            long_ += lt; details.append(f"{suit} long+{lt:.1f}")
        if mode == "HOKUM" and n == 1 and trump_n > 0 and suit != trump_suit:
            ruff += 0.5; details.append(f"sing {suit}+0.5R")

    if mode == "HOKUM" and trump_suit:
        spare_trumps = trump_n - _trump_qt(groups.get(trump_suit, []))
        ruff = min(ruff, max(0, spare_trumps))
    expected = quick + long_ * 0.7 + ruff * 0.8
    min_t = floor(quick)
    max_t = min(8, floor(quick + long_ + ruff))
    losers = max(0.0, len(hand) - quick - long_ - ruff)
    return {
        "min_tricks": min_t, "expected_tricks": round(expected, 2),
        "max_tricks": max_t, "quick_tricks": quick, "long_tricks": long_,
        "ruff_tricks": ruff, "losers": round(losers, 2),
        "detail": f"QT={quick:.1f} LT={long_:.1f} RT={ruff:.1f} | {'; '.join(details)}",
    }
