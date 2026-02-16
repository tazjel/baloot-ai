"""Score-pressure heuristics for Baloot AI bidding.

In Baloot, a match is won by the first team to reach 152 points across
multiple rounds.  These pure functions translate the current match score
into actionable adjustments for the bidding evaluator — loosening
thresholds when desperate and tightening them when comfortably ahead.

Empirical calibration from 109 professional games (1,095 rounds):
- Pros bid 85.4% PASS overall — they are VERY selective
- Tied scores → most aggressive bidding (18.8% bid rate)
- Far ahead → most conservative bidding (13.0% bid rate)
- Far behind → moderate desperation bidding (14.0% bid rate)
"""
from __future__ import annotations

from ai_worker.strategies.components.pro_data import (
    DOUBLING_BY_SCORE_STATE, SCORE_BID_ADJUSTMENT,
    HOKUM_WIN_PROB, SUN_WIN_PROB, TRUMP_COUNT_WIN_FACTOR,
)

WIN_THRESHOLD: int = 152

# Empirically calibrated situations from pro data:
# bid_adj: threshold adjustment (negative = more aggressive)
# dbl_bias: doubling bias from DOUBLING_BY_SCORE_STATE
#                    (label,        bid_adj, doubling_bias)
_SITUATIONS: list[tuple[str, float, float]] = [
    # DESPERATE: them ≥ 140, us < 100 → pros double 97% of the time
    ("DESPERATE",    -0.15,  +0.20),
    # TRAILING: us < them - 30 → moderate aggression
    ("TRAILING",     -0.08,  +0.05),
    # CLOSE: within 15 pts or tied → pros are most aggressive (18.8% bid rate)
    ("CLOSE",         0.00,   0.00),
    # LEADING: us > them + 30 → pros are conservative (13.0% bid rate)
    ("LEADING",      +0.05,  -0.12),
    # MATCH_POINT: us ≥ 140 → go for the win but protect lead
    ("MATCH_POINT",  -0.05,  +0.15),
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


def _score_state_key(us: int, them: int) -> str:
    """Map score to pro_data doubling score-state key."""
    diff = us - them
    if abs(diff) <= 15:
        return "tied"
    if diff > 30:
        return "far_ahead"
    if diff > 0:
        return "slightly_ahead"
    if diff < -30:
        return "far_behind"
    return "slightly_behind"


def get_score_pressure(us_score: int, them_score: int) -> dict[str, object]:
    """Quantify how the match score should shift bidding aggression.

    Returns 'situation' label, 'bid_threshold_adjustment' (added to the
    base hand-strength threshold), and 'doubling_bias' (added to the
    doubling decision score).  Also returns 'pro_doubling_rate' — the
    empirical frequency at which pros double in this score state.
    """
    label, bid_adj, dbl_bias = _SITUATIONS[_classify(us_score, them_score)]

    # Empirical doubling rate from pro data
    state_key = _score_state_key(us_score, them_score)
    pro_dbl_rate = DOUBLING_BY_SCORE_STATE.get(state_key, 0.5)

    return {
        "situation": label,
        "bid_threshold_adjustment": bid_adj,
        "doubling_bias": dbl_bias,
        "pro_doubling_rate": pro_dbl_rate,
        "score_state": state_key,
    }


def get_win_probability(trump_count: int, high_cards: int, mode: str = "HOKUM") -> float:
    """Lookup empirical P(win) from pro data for hand shape.

    Returns probability 0.0-1.0 from the pro game database.
    Falls back to trump-count-only model if hand shape isn't in the lookup.
    """
    key = f"{trump_count}t_{high_cards}h"
    table = HOKUM_WIN_PROB if mode == "HOKUM" else SUN_WIN_PROB
    prob = table.get(key)
    if prob is not None:
        return prob

    # Fallback: use combined trump count factor
    if mode == "HOKUM":
        return TRUMP_COUNT_WIN_FACTOR.get(min(trump_count, 6), 0.70)

    # SUN fallback: base 70% adjusted by high card count
    return min(0.90, 0.60 + high_cards * 0.05)


def should_gamble(
    us_score: int, them_score: int, hand_strength: float, bid_type: str,
) -> bool:
    """Decide whether to bid on a borderline hand given match pressure.

    Returns True only in do-or-die situations: when opponents are about
    to win and we must act, or when we can close the match ourselves.

    Empirical insight: pros bid 14.0% when far behind (vs 13.0% far ahead),
    showing moderate desperation but not recklessness.
    """
    # Desperate: opponents close to winning
    if them_score >= 145 and us_score < 120:
        return True
    # Match point: we can close it out with a decent hand
    if us_score >= 145 and hand_strength > 0.35:
        return True
    # Far behind: gamble on slightly weaker hands
    if them_score > us_score + 50 and hand_strength > 0.40:
        return True
    return False
