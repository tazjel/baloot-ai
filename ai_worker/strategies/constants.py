"""
Shared constants for all AI strategy modules.

Single source of truth — mirrors game_engine/models/constants.py values.
Strategy components import from HERE instead of duplicating locally.
"""
from __future__ import annotations

# ── Suits ────────────────────────────────────────────────────────────────
ALL_SUITS = ["♠", "♥", "♦", "♣"]

# ── Rank ordering (low → high) for trick comparison ─────────────────────
ORDER_SUN = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]

# ── Point values per rank (Abnat) ───────────────────────────────────────
# Compact form (zero-value ranks omitted) — used by most strategy modules
PTS_SUN = {"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2}
PTS_HOKUM = {"J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3}

# Full form (all 8 ranks including zeros) — used by endgame solver
PTS_SUN_FULL = {"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2, "9": 0, "8": 0, "7": 0}
PTS_HOKUM_FULL = {"J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3, "8": 0, "7": 0}

# ── Scoring totals ──────────────────────────────────────────────────────
TOTAL_ABNAT_SUN = 130       # 120 card pts + 10 last trick
TOTAL_ABNAT_HOKUM = 162     # 152 card pts + 10 last trick
TOTAL_GP_SUN = 26
TOTAL_GP_HOKUM = 16
LAST_TRICK_BONUS = 10
MATCH_TARGET = 152
