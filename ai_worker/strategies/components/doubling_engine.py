"""Doubling (challenge) decision engine for Baloot AI.

Evaluates whether to double an opponent's SUN or HOKUM bid by scoring
trump control, Ace coverage, and distribution.  Score-aware thresholds
adjust aggression based on match state.  Wrong doubles cost ~200 points.

Empirical calibration from 109 professional games:
- Base double (×2): 34.7% win rate → Kelly = -0.31 (NEGATIVE expected value!)
- Triple (×3): 66.7% win rate → Kelly = +0.33 (good bet)
- Quadruple (×4): 42.9% win rate → Kelly = -0.14 (bad bet)
- Qahwa (all-in): 66.7% win rate → expert-only
- Pros double 100% when tied, 97% when far behind, only 50% when far ahead
"""
from __future__ import annotations
from collections import Counter
from ai_worker.strategies.components.pro_data import (
    DOUBLING_WIN_RATE, DOUBLING_BY_SCORE_STATE,
)


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


def _score_state_key(my: int, their: int) -> str:
    """Map match score to pro_data doubling score-state key."""
    diff = my - their
    if abs(diff) <= 15:
        return "tied"
    if diff > 30:
        return "far_ahead"
    if diff > 0:
        return "slightly_ahead"
    if diff < -30:
        return "far_behind"
    return "slightly_behind"


def _sfactor(my: int, their: int) -> tuple[float, str]:
    """Threshold multiplier from match score, empirically calibrated.

    Pros double 100% when tied, 97% far behind, only 50% far ahead.
    We translate this into threshold multipliers:
    - High pro doubling rate → lower threshold (aggressive)
    - Low pro doubling rate → higher threshold (conservative)
    """
    state = _score_state_key(my, their)
    pro_rate = DOUBLING_BY_SCORE_STATE.get(state, 0.5)

    # Map pro doubling rate to threshold multiplier:
    # 1.0 (always double) → factor 0.85 (very aggressive)
    # 0.5 (50% double) → factor 1.15 (conservative)
    factor = 1.30 - (pro_rate * 0.45)
    label = f"{state}({pro_rate:.0%})→×{factor:.2f}"
    return factor, label


def _kelly_check(doubling_level: int) -> tuple[bool, str]:
    """Kelly Criterion check: is this doubling level +EV from pro data?

    Returns (is_positive_kelly, explanation).
    """
    wr = DOUBLING_WIN_RATE.get(doubling_level, 0.5)
    # Kelly fraction: f* = (bp - q) / b where b=1 (even money), p=win_rate, q=1-p
    # Simplified: f* = 2*p - 1 for even-money bets
    kelly = 2 * wr - 1
    is_positive = kelly > 0
    return is_positive, f"level={doubling_level} WR={wr:.0%} Kelly={kelly:+.2f}"


def should_double(
    hand: list, bid_type: str, trump_suit: str | None = None,
    my_score: int = 0, their_score: int = 0, partner_passed: bool = True,
    current_doubling_level: int = 1,
) -> dict:
    """Decide whether to double an opponent's bid.

    Computes 0-100 defensive strength, applies match-score adjustment
    and Kelly Criterion validation from pro data.

    Kelly insight: base double (×2) has NEGATIVE Kelly (-0.31) in pro data,
    meaning pros lose money on average when doubling. Only double with
    genuinely strong defensive hands.
    """
    raw, notes = _sun_str(hand) if bid_type == "SUN" else _hokum_str(hand, trump_suit or "")
    conf_adj = 0.0
    if partner_passed: conf_adj = -0.1; notes.append("partner pass→-0.1")

    sf, sfn = _sfactor(my_score, their_score)
    if sfn: notes.append(sfn)
    threshold = 50 * sf

    # Kelly Criterion check: is this doubling level +EV?
    next_level = current_doubling_level + 1
    kelly_ok, kelly_note = _kelly_check(next_level)
    notes.append(kelly_note)

    # If Kelly is negative for this level, raise the confidence requirement
    # This prevents doubling into -EV situations unless hand is extremely strong
    conf_floor = 0.6
    if not kelly_ok:
        conf_floor = 0.75  # Require much higher confidence for -EV doubles
        notes.append("Kelly-→conf≥0.75")

    confidence = min(1.0, max(0.0, (raw - 20) / 80 + conf_adj))

    # Pro score-state gate: if pros only double 50% in this state,
    # we need extra confidence to justify it
    state = _score_state_key(my_score, their_score)
    pro_rate = DOUBLING_BY_SCORE_STATE.get(state, 0.5)
    if pro_rate < 0.6:
        conf_floor = max(conf_floor, 0.70)
        notes.append(f"low-pro-rate({pro_rate:.0%})→conf≥0.70")

    do = raw >= threshold and confidence >= conf_floor
    r = f"str={raw:.0f} thr={threshold:.0f} conf={confidence:.2f} | {'; '.join(notes)}"
    return {"should_double": do, "confidence": round(confidence, 2), "reasoning": r}


def should_redouble(
    hand: list, bid_type: str, trump_suit: str | None = None,
    my_score: int = 0, their_score: int = 0,
) -> dict:
    """Decide whether to redouble after opponents doubled our bid.

    Only redouble at extreme confidence (×4 stakes demand near-certainty).

    Kelly insight: quadruple (×4) has negative Kelly (-0.14) in pro data.
    Only redouble with truly dominant hands.
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

    # Kelly check for ×4 level — it's negative (-0.14)!
    kelly_ok, kelly_note = _kelly_check(4)
    notes.append(kelly_note)

    threshold = 70 * sf
    # Raise threshold if Kelly is negative (it is for ×4)
    if not kelly_ok:
        threshold *= 1.15
        notes.append("Kelly-→thr×1.15")

    confidence = min(1.0, max(0.0, (raw - 30) / 70))
    do = raw >= threshold and confidence >= 0.8
    r = f"str={raw:.0f} thr={threshold:.0f} conf={confidence:.2f} | {'; '.join(notes)}"
    return {"should_redouble": do, "confidence": round(confidence, 2), "reasoning": r}
