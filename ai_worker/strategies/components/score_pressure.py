"""Score-pressure heuristics for Baloot AI bidding.

In Baloot, a match is won by the first team to reach 152 points across
multiple rounds.  These pure functions translate the current match score
into actionable adjustments for the bidding evaluator — loosening
thresholds when desperate and tightening them when comfortably ahead.
"""
from __future__ import annotations

WIN_THRESHOLD: int = 152
#                    (label,        bid_adj, doubling_bias)
_SITUATIONS: list[tuple[str, float, float]] = [
    ("DESPERATE",    -0.15,  +0.15),
    ("TRAILING",     -0.08,   0.00),
    ("CLOSE",         0.00,   0.00),
    ("LEADING",      +0.05,  -0.10),
    ("MATCH_POINT",  -0.05,  +0.20),
]


def _classify(us: int, them: int) -> int:
    """Return index into _SITUATIONS for the current score line."""
    if them >= 140 and us < 100:
        return 0  # DESPERATE
    if us >= 140:
        return 4  # MATCH_POINT
    if us < them - 30:
        return 1  # TRAILING
    if us > them + 30:
        return 3  # LEADING
    return 2      # CLOSE


def get_score_pressure(us_score: int, them_score: int) -> dict[str, object]:
    """Quantify how the match score should shift bidding aggression.

    Returns 'situation' label, 'bid_threshold_adjustment' (added to the
    base hand-strength threshold), and 'doubling_bias' (added to the
    doubling decision score).
    """
    label, bid_adj, dbl_bias = _SITUATIONS[_classify(us_score, them_score)]
    return {
        "situation": label,
        "bid_threshold_adjustment": bid_adj,
        "doubling_bias": dbl_bias,
    }


def should_gamble(
    us_score: int, them_score: int, hand_strength: float, bid_type: str,
) -> bool:
    """Decide whether to bid on a borderline hand given match pressure.

    Returns True only in do-or-die situations: when opponents are about
    to win and we must act, or when we can close the match ourselves.
    *bid_type* ('SUN'|'HOKUM') accepted for future mode-specific tuning.
    """
    if them_score >= 145 and us_score < 120:
        return True
    return us_score >= 145 and hand_strength > 0.35
