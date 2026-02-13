"""Doubling (challenge) decision engine for Baloot AI.

Evaluates whether to double an opponent's SUN or HOKUM bid by scoring
trump control, Ace coverage, and distribution.  Score-aware thresholds
adjust aggression based on match state.  Wrong doubles cost ~200 points.
"""
from __future__ import annotations
from collections import Counter


def _sun_str(hand: list) -> tuple[float, list[str]]:
    """Defensive strength vs SUN bid (0-100)."""
    suits = Counter(c.suit for c in hand)
    rc = Counter(c.rank for c in hand)
    s, n = 0.0, []
    aces, tens = rc.get("A", 0), rc.get("10", 0)
    s += aces * 25 + tens * 10
    n.append(f"{aces}A={aces*25} {tens}T={tens*10}")
    for c in hand:
        if c.rank == "K" and suits[c.suit] >= 2: s += 5; n.append(f"K{c.suit}+5")
    for suit, cnt in suits.items():
        if cnt >= 5: s += 10; n.append(f"{suit}×{cnt}+10")
    return s, n


def _hokum_str(hand: list, trump: str) -> tuple[float, list[str]]:
    """Defensive strength vs HOKUM bid (0-100)."""
    tr = {c.rank for c in hand if c.suit == trump}
    t_n = sum(1 for c in hand if c.suit == trump)
    sides = [c for c in hand if c.suit != trump]
    all_side = {"♠", "♥", "♦", "♣"} - {trump}
    s, n = 0.0, []
    if "J" in tr: s += 30; n.append("tJ=30")
    if "9" in tr: s += 25; n.append("t9=25")
    if "A" in tr: s += 10; n.append("tA=10")
    extra = max(0, t_n - 2)
    if extra: s += extra * 8; n.append(f"+{extra}t={extra*8}")
    sa = sum(1 for c in sides if c.rank == "A")
    if sa: s += sa * 15; n.append(f"{sa}sA={sa*15}")
    voids = all_side - {c.suit for c in sides}
    if voids: s += len(voids) * 10; n.append(f"{len(voids)}void={len(voids)*10}")
    return s, n


def _sfactor(my: int, their: int) -> tuple[float, str]:
    """Threshold multiplier from match score (>1 = conservative)."""
    if my == 2 and their == 2: return 1.15, "match-point→conserv"
    if their >= 2 and my < 2: return 0.90, "behind→aggro"
    if my >= 2 and their < 2: return 1.10, "ahead→protect"
    return 1.0, ""


def should_double(
    hand: list, bid_type: str, trump_suit: str | None = None,
    my_score: int = 0, their_score: int = 0, partner_passed: bool = True,
) -> dict:
    """Decide whether to double an opponent's bid.

    Computes 0-100 defensive strength, applies match-score adjustment,
    returns bool with confidence and reasoning.
    """
    raw, notes = _sun_str(hand) if bid_type == "SUN" else _hokum_str(hand, trump_suit or "")
    conf_adj = 0.0
    if partner_passed: conf_adj = -0.1; notes.append("partner pass→-0.1")
    sf, sfn = _sfactor(my_score, their_score)
    if sfn: notes.append(sfn)
    threshold = 50 * sf
    confidence = min(1.0, max(0.0, (raw - 20) / 80 + conf_adj))
    do = raw >= threshold and confidence >= 0.6
    r = f"str={raw:.0f} thr={threshold:.0f} conf={confidence:.2f} | {'; '.join(notes)}"
    return {"should_double": do, "confidence": round(confidence, 2), "reasoning": r}


def should_redouble(
    hand: list, bid_type: str, trump_suit: str | None = None,
    my_score: int = 0, their_score: int = 0,
) -> dict:
    """Decide whether to redouble after opponents doubled our bid.

    Only redouble at extreme confidence (×4 stakes demand near-certainty).
    """
    if bid_type == "SUN":
        rc = Counter(c.rank for c in hand)
        suits = Counter(c.suit for c in hand)
        raw = rc.get("A", 0) * 20 + rc.get("10", 0) * 15
        raw += 10 if max(suits.values(), default=0) <= 3 else 0
        notes = [f"{rc.get('A',0)}A {rc.get('10',0)}T raw={raw}"]
    else:
        tr = {c.rank for c in hand if c.suit == (trump_suit or "")}
        t_n = sum(1 for c in hand if c.suit == (trump_suit or ""))
        raw = (35 if "J" in tr else 0) + (25 if "9" in tr else 0) + t_n * 8
        raw += sum(10 for c in hand if c.suit != trump_suit and c.rank == "A")
        notes = [f"t={t_n} J={'Y' if 'J' in tr else 'N'} 9={'Y' if '9' in tr else 'N'} raw={raw}"]
    sf, sfn = _sfactor(my_score, their_score)
    if sfn: notes.append(sfn)
    threshold = 70 * sf
    confidence = min(1.0, max(0.0, (raw - 30) / 70))
    do = raw >= threshold and confidence >= 0.8
    r = f"str={raw:.0f} thr={threshold:.0f} conf={confidence:.2f} | {'; '.join(notes)}"
    return {"should_redouble": do, "confidence": round(confidence, 2), "reasoning": r}
