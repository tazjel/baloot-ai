"""Professional player data — empirical thresholds mined from 109 pro games.

This module provides lookup tables and calibration constants derived from
the data mining pipeline (scripts/data_mining/). All values are empirical
averages from 10,698 human bids, 32,449 plays, and 1,095 round outcomes.

Usage: import from this module; never read JSON at runtime.
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════
#  BIDDING THRESHOLDS (from mine_bidding_data.py)
#  Key: "{trump_count}t_{high_cards}h" → (bid_pct, win_pct)
#  bid_pct = how often pros bid with this hand shape
#  win_pct = contract win rate when they DO bid
# ═══════════════════════════════════════════════════════════════════

# Hokum Round 1: (trump_count, high_cards) → (bid_frequency, win_rate)
HOKUM_R1_THRESHOLD: dict[str, tuple[float, float]] = {
    "0t_0h": (0.000, 0.000),
    "0t_1h": (0.002, 0.500),
    "0t_2h": (0.003, 0.667),
    "1t_0h": (0.001, 0.000),
    "1t_1h": (0.005, 0.600),
    "1t_2h": (0.011, 0.700),
    "1t_3h": (0.032, 0.750),
    "2t_1h": (0.019, 0.615),
    "2t_2h": (0.064, 0.684),
    "2t_3h": (0.188, 0.684),
    "2t_4h": (0.333, 0.750),
    "3t_2h": (0.158, 0.750),
    "3t_3h": (0.439, 0.800),
    "3t_4h": (0.600, 0.833),
    "3t_5h": (0.714, 0.800),
    "4t_2h": (0.400, 0.750),
    "4t_3h": (0.619, 0.769),
    "4t_4h": (0.750, 0.833),
    "4t_5h": (0.857, 0.879),
    "5t_3h": (1.000, 1.000),
    "5t_4h": (1.000, 0.900),
    "5t_5h": (1.000, 0.947),
    "6t_6h": (1.000, 1.000),
}

# Position multiplier: seat position relative to dealer
# Pos 1 = first to bid (conservative), Pos 4 = dealer (most information)
POSITION_MULTIPLIER: dict[int, float] = {
    1: 0.85,   # First to bid: conservative (9.9% raw rate)
    2: 1.00,   # Second: baseline
    3: 1.15,   # Third: slightly more info
    4: 1.40,   # Dealer (last to speak): 2.7x advantage (26.7% raw rate)
}

# Score-state bidding adjustment: how match score affects bid willingness
# Positive = more aggressive (lower threshold), negative = more conservative
SCORE_BID_ADJUSTMENT: dict[str, float] = {
    "tied":        +0.03,    # 18.8% rate — most aggressive
    "slightly_behind": +0.01,
    "far_behind":  +0.02,    # 14.0% rate — moderate desperation
    "slightly_ahead": -0.01,
    "far_ahead":   -0.03,    # 13.0% rate — conservative
}

# ═══════════════════════════════════════════════════════════════════
#  WIN PROBABILITY LOOKUP (from mine_round_outcomes.py)
#  Key: "{trump_count}t_{high_cards}h" → P(win)
# ═══════════════════════════════════════════════════════════════════

HOKUM_WIN_PROB: dict[str, float] = {
    "2t_3h": 0.833,
    "2t_4h": 0.750,
    "3t_3h": 0.800,
    "3t_4h": 0.833,
    "3t_5h": 0.796,
    "4t_3h": 0.769,
    "4t_4h": 0.833,
    "4t_5h": 0.879,
    "5t_3h": 1.000,
    "5t_4h": 0.900,
    "5t_5h": 0.947,
    "6t_6h": 1.000,
}

SUN_WIN_PROB: dict[str, float] = {
    "0t_3h": 0.667,
    "0t_4h": 0.706,
    "0t_5h": 0.714,
    "0t_6h": 0.722,
    "0t_7h": 0.735,
    "0t_8h": 0.800,
}

# Combined trump count (bidder + partner) → overall win probability
TRUMP_COUNT_WIN_FACTOR: dict[int, float] = {
    0: 0.701,
    1: 0.745,
    2: 0.810,
    3: 0.858,
    4: 0.870,
    5: 0.885,
    6: 1.000,
}

# ═══════════════════════════════════════════════════════════════════
#  LEAD PATTERNS (from mine_card_play_data.py)
#  Trick-dependent lead rank preferences
# ═══════════════════════════════════════════════════════════════════

# Lead rank preference weights by trick number (1-indexed)
# Higher weight = pros lead this rank more often at this trick
LEAD_RANK_BY_TRICK: dict[int, dict[str, float]] = {
    1: {"A": 0.402, "J": 0.180, "K": 0.091, "10": 0.085, "9": 0.085, "Q": 0.065, "8": 0.050, "7": 0.042},
    2: {"A": 0.192, "10": 0.183, "9": 0.154, "J": 0.124, "K": 0.113, "Q": 0.095, "8": 0.082, "7": 0.057},
    3: {"A": 0.211, "J": 0.136, "9": 0.134, "10": 0.129, "K": 0.115, "Q": 0.108, "8": 0.098, "7": 0.069},
    4: {"A": 0.188, "10": 0.147, "9": 0.137, "K": 0.134, "Q": 0.121, "J": 0.113, "8": 0.092, "7": 0.068},
    5: {"A": 0.175, "K": 0.147, "10": 0.143, "Q": 0.128, "J": 0.118, "9": 0.115, "8": 0.098, "7": 0.076},
    6: {"A": 0.165, "K": 0.155, "10": 0.151, "Q": 0.130, "9": 0.120, "J": 0.110, "8": 0.095, "7": 0.074},
    7: {"K": 0.172, "10": 0.165, "A": 0.160, "J": 0.128, "Q": 0.125, "9": 0.105, "8": 0.085, "7": 0.060},
    8: {"K": 0.176, "10": 0.171, "J": 0.134, "A": 0.132, "Q": 0.128, "9": 0.108, "8": 0.088, "7": 0.063},
}

# Hokum trump lead frequency: 27.2% of all leads in HOKUM games
HOKUM_TRUMP_LEAD_PCT: float = 0.272

# Bidder vs defender lead preference
BIDDER_LEAD_RANK_ORDER: list[str] = ["A", "10", "J", "K", "9", "Q", "8", "7"]
DEFENDER_LEAD_RANK_ORDER: list[str] = ["A", "K", "10", "J", "Q", "9", "8", "7"]

# ═══════════════════════════════════════════════════════════════════
#  DISCARD SIGNALS (from mine_signals.py)
#  Empirical reliability of discard patterns
# ═══════════════════════════════════════════════════════════════════

# When void, pros discard from their shortest suit 78.5% of the time
DISCARD_SHORTEST_SUIT_RELIABILITY: float = 0.785

# When discarding, pros play their highest card in that suit 66.3% of the time
DISCARD_HIGHEST_IN_SUIT_RELIABILITY: float = 0.663

# Lead signal reliability (NOT reliable — don't use for inference)
ACE_LEAD_HAS_KING_RELIABILITY: float = 0.138  # Only 13.8%
LOW_LEAD_FROM_LENGTH_RELIABILITY: float = 0.085  # Only 8.5%

# Discard rank distribution when void
VOID_DISCARD_LOW_PCT: float = 0.471    # 7/8/9 discarded 47.1%
VOID_DISCARD_HIGH_PCT: float = 0.259   # A/10/K discarded 25.9%
VOID_DISCARD_MID_PCT: float = 0.270    # Q/J discarded 27.0%

# ═══════════════════════════════════════════════════════════════════
#  DOUBLING THRESHOLDS (from mine_doubling_data.py)
#  Kelly-validated doubling decision data
# ═══════════════════════════════════════════════════════════════════

# Win rate by doubling level
DOUBLING_WIN_RATE: dict[int, float] = {
    2:  0.347,   # Base double — negative Kelly (-0.31)
    3:  0.667,   # Triple — positive Kelly (+0.33)
    4:  0.429,   # Quadruple — negative Kelly (-0.14)
    99: 0.667,   # Qahwa — expert-only, high reward
}

# Score-state doubling frequency (how often pros double by score state)
DOUBLING_BY_SCORE_STATE: dict[str, float] = {
    "tied":            1.000,  # Always double when tied
    "slightly_behind": 0.810,  # 81%
    "far_behind":      0.970,  # 97% — desperation doubles
    "slightly_ahead":  0.571,  # 57%
    "far_ahead":       0.500,  # Only 50% — conservative
}

# ═══════════════════════════════════════════════════════════════════
#  KABOOT PREDICTORS (from mine_round_outcomes.py)
# ═══════════════════════════════════════════════════════════════════

# Kaboot (sweep) probability by mode
KABOOT_RATE_SUN: float = 0.138    # 13.8% of SUN rounds
KABOOT_RATE_HOKUM: float = 0.093  # 9.3% of HOKUM rounds

# Overall pass rate (pros are VERY selective)
PRO_PASS_RATE: float = 0.854      # 85.4% of all decisions are PASS


def get_pro_bid_frequency(trump_count: int, high_cards: int) -> float:
    """Return pro bid frequency for given hand shape. 0.0 if not in lookup."""
    key = f"{trump_count}t_{high_cards}h"
    entry = HOKUM_R1_THRESHOLD.get(key)
    return entry[0] if entry else 0.0


def get_pro_win_rate(trump_count: int, high_cards: int, mode: str = "HOKUM") -> float:
    """Return pro contract win rate for given hand shape."""
    key = f"{trump_count}t_{high_cards}h"
    table = HOKUM_WIN_PROB if mode == "HOKUM" else SUN_WIN_PROB
    return table.get(key, 0.70)  # Default 70% if not in lookup


def get_position_multiplier(seat_position: int) -> float:
    """Return bidding frequency multiplier for seat position (1-4)."""
    return POSITION_MULTIPLIER.get(seat_position, 1.0)


def get_lead_weight(trick_number: int, rank: str) -> float:
    """Return pro lead frequency weight for rank at given trick number."""
    trick_data = LEAD_RANK_BY_TRICK.get(trick_number, LEAD_RANK_BY_TRICK.get(4, {}))
    return trick_data.get(rank, 0.05)
