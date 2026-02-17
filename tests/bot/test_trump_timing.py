"""Tests for M31 — Trump Timing, Singleton Detection, and Discard Signals.

Validates:
1. trump_manager respects pro trump conservation curve
2. opponent_model detects singleton suspects from first leads
3. opponent_model reads discard signals
4. partner_read reads discard signals
5. pro_data constants are present and sensible
"""
from __future__ import annotations
import pytest
from types import SimpleNamespace

from ai_worker.strategies.components.trump_manager import manage_trumps
from ai_worker.strategies.components.opponent_model import model_opponents
from ai_worker.strategies.components.partner_read import read_partner
from ai_worker.strategies.components.pro_data import (
    TRUMP_IN_BY_TRICK, SINGLETON_LEAD_RANKS,
)


def _card(rank: str, suit: str):
    return SimpleNamespace(rank=rank, suit=suit)


# ═══════════════════════════════════════════════════════════════
#  TRUMP MANAGER — TRICK-AWARE DRAW DECISIONS
# ═══════════════════════════════════════════════════════════════

class TestTrumpTimingAwareness:
    """Verify trump_manager uses pro conservation curve."""

    def _make_hand(self, trumps: list[str], trump_suit: str, sides: list[tuple[str, str]] | None = None):
        hand = [_card(r, trump_suit) for r in trumps]
        for r, s in (sides or []):
            hand.append(_card(r, s))
        return hand

    def test_early_game_single_honor_3_trumps_draws(self):
        """Trick 1-3: J + 3 trumps should DRAW (pro rate ~43-26%)."""
        hand = self._make_hand(["J", "8", "7"], "♠", [("A", "♥"), ("K", "♥"), ("10", "♦"), ("A", "♣"), ("7", "♣")])
        result = manage_trumps(
            hand, "♠", my_trumps=3, enemy_trumps_estimate=3,
            partner_trumps_estimate=1, tricks_played=1, we_are_buyers=True,
            partner_void_suits=[], enemy_void_suits=[],
        )
        assert result["lead_trump"] is True
        assert result["phase"] == "PARTIAL_DRAW"

    def test_late_game_single_honor_3_trumps_preserves(self):
        """Trick 5+: J + only 3 trumps should NOT draw (pro rate ~24%)."""
        hand = self._make_hand(["J", "8", "7"], "♠", [("A", "♥"), ("K", "♦")])
        result = manage_trumps(
            hand, "♠", my_trumps=3, enemy_trumps_estimate=2,
            partner_trumps_estimate=1, tricks_played=5, we_are_buyers=True,
            partner_void_suits=[], enemy_void_suits=[],
        )
        # Should NOT lead trump — late game with only 3 trumps
        assert result["lead_trump"] is False

    def test_late_game_single_honor_4_trumps_draws(self):
        """Trick 5+: J + 4 trumps should STILL draw (strong enough)."""
        hand = self._make_hand(["J", "8", "7", "Q"], "♠", [("A", "♥")])
        result = manage_trumps(
            hand, "♠", my_trumps=4, enemy_trumps_estimate=2,
            partner_trumps_estimate=1, tricks_played=5, we_are_buyers=True,
            partner_void_suits=[], enemy_void_suits=[],
        )
        assert result["lead_trump"] is True
        assert result["phase"] == "PARTIAL_DRAW"

    def test_j9_always_draws_regardless_of_trick(self):
        """J+9 together should always draw regardless of trick number."""
        hand = self._make_hand(["J", "9", "7"], "♠", [("A", "♥"), ("K", "♦"), ("10", "♣"), ("8", "♣"), ("7", "♥")])
        for trick in [0, 3, 6]:
            result = manage_trumps(
                hand, "♠", my_trumps=3, enemy_trumps_estimate=2,
                partner_trumps_estimate=1, tricks_played=trick, we_are_buyers=True,
                partner_void_suits=[], enemy_void_suits=[],
            )
            assert result["lead_trump"] is True, f"J+9 should draw at trick {trick}"


# ═══════════════════════════════════════════════════════════════
#  OPPONENT MODEL — SINGLETON DETECTION
# ═══════════════════════════════════════════════════════════════

class TestSingletonDetection:
    """Verify opponent_model detects singleton suspects from first leads."""

    def test_singleton_detection_ten(self):
        """Opponent leads 10♦ first time → ♦ in singleton_suspects."""
        tricks = [
            {"leader": "Right", "cards": [
                {"playedBy": "Right", "card": {"rank": "10", "suit": "♦"}},
                {"playedBy": "Top", "card": {"rank": "7", "suit": "♦"}},
                {"playedBy": "Left", "card": {"rank": "8", "suit": "♦"}},
                {"playedBy": "Bottom", "card": {"rank": "A", "suit": "♦"}},
            ]},
        ]
        result = model_opponents("Bottom", [], tricks, "HOKUM", "♠")
        right_profile = result["opponents"]["Right"]
        assert "♦" in right_profile["singleton_suspects"]

    def test_singleton_detection_ace(self):
        """Opponent leads A♣ first time → ♣ in singleton_suspects."""
        tricks = [
            {"leader": "Left", "cards": [
                {"playedBy": "Left", "card": {"rank": "A", "suit": "♣"}},
                {"playedBy": "Bottom", "card": {"rank": "7", "suit": "♣"}},
                {"playedBy": "Right", "card": {"rank": "8", "suit": "♣"}},
                {"playedBy": "Top", "card": {"rank": "K", "suit": "♣"}},
            ]},
        ]
        result = model_opponents("Bottom", [], tricks, "HOKUM", "♠")
        left_profile = result["opponents"]["Left"]
        assert "♣" in left_profile["singleton_suspects"]

    def test_no_singleton_for_trump_suit(self):
        """Leading 10 in trump suit should NOT trigger singleton detection."""
        tricks = [
            {"leader": "Right", "cards": [
                {"playedBy": "Right", "card": {"rank": "10", "suit": "♠"}},
                {"playedBy": "Top", "card": {"rank": "7", "suit": "♠"}},
                {"playedBy": "Left", "card": {"rank": "8", "suit": "♠"}},
                {"playedBy": "Bottom", "card": {"rank": "J", "suit": "♠"}},
            ]},
        ]
        result = model_opponents("Bottom", [], tricks, "HOKUM", "♠")
        right_profile = result["opponents"]["Right"]
        assert "♠" not in right_profile["singleton_suspects"]

    def test_no_singleton_for_low_lead(self):
        """Leading 7♦ should NOT trigger singleton detection."""
        tricks = [
            {"leader": "Right", "cards": [
                {"playedBy": "Right", "card": {"rank": "7", "suit": "♦"}},
                {"playedBy": "Top", "card": {"rank": "8", "suit": "♦"}},
                {"playedBy": "Left", "card": {"rank": "K", "suit": "♦"}},
                {"playedBy": "Bottom", "card": {"rank": "A", "suit": "♦"}},
            ]},
        ]
        result = model_opponents("Bottom", [], tricks, "HOKUM", "♠")
        right_profile = result["opponents"]["Right"]
        assert "♦" not in right_profile["singleton_suspects"]


# ═══════════════════════════════════════════════════════════════
#  OPPONENT MODEL — DISCARD SIGNALS
# ═══════════════════════════════════════════════════════════════

class TestOpponentDiscardSignals:
    """Verify opponent_model reads discard suit signals."""

    def test_discard_reduces_suit_strength(self):
        """Opponent discards ♣7 when void in ♠ → ♣ strength reduced."""
        tricks = [
            {"leader": "Bottom", "cards": [
                {"playedBy": "Bottom", "card": {"rank": "A", "suit": "♠"}},
                {"playedBy": "Right", "card": {"rank": "7", "suit": "♣"}},  # discard ♣
                {"playedBy": "Top", "card": {"rank": "K", "suit": "♠"}},
                {"playedBy": "Left", "card": {"rank": "8", "suit": "♠"}},
            ]},
        ]
        result = model_opponents("Bottom", [], tricks, "HOKUM", "♥")
        right_str = result["opponents"]["Right"]["strength_by_suit"]
        # ♣ strength should be negative (discarded = short suit signal)
        assert right_str["♣"] < 0.0

    def test_high_discard_extra_penalty(self):
        """Opponent discards A♦ → ♦ strength reduced more than low discard."""
        tricks_high = [
            {"leader": "Bottom", "cards": [
                {"playedBy": "Bottom", "card": {"rank": "A", "suit": "♠"}},
                {"playedBy": "Right", "card": {"rank": "A", "suit": "♦"}},  # high discard
                {"playedBy": "Top", "card": {"rank": "K", "suit": "♠"}},
                {"playedBy": "Left", "card": {"rank": "8", "suit": "♠"}},
            ]},
        ]
        tricks_low = [
            {"leader": "Bottom", "cards": [
                {"playedBy": "Bottom", "card": {"rank": "A", "suit": "♠"}},
                {"playedBy": "Right", "card": {"rank": "7", "suit": "♦"}},  # low discard
                {"playedBy": "Top", "card": {"rank": "K", "suit": "♠"}},
                {"playedBy": "Left", "card": {"rank": "8", "suit": "♠"}},
            ]},
        ]
        result_high = model_opponents("Bottom", [], tricks_high, "HOKUM", "♥")
        result_low = model_opponents("Bottom", [], tricks_low, "HOKUM", "♥")
        str_high = result_high["opponents"]["Right"]["strength_by_suit"]["♦"]
        str_low = result_low["opponents"]["Right"]["strength_by_suit"]["♦"]
        # High-card discard should reduce strength MORE than low-card
        assert str_high < str_low


# ═══════════════════════════════════════════════════════════════
#  PARTNER READ — DISCARD SIGNALS
# ═══════════════════════════════════════════════════════════════

class TestPartnerDiscardSignals:
    """Verify partner_read reads discard suit signals."""

    def test_partner_discard_reduces_suit_strength(self):
        """Partner discards ♣7 when void in ♠ → ♣ strength reduced."""
        tricks = [
            {"leader": "Bottom", "cards": [
                {"position": "Bottom", "suit": "♠", "rank": "A"},
                {"position": "Right", "suit": "♠", "rank": "K"},
                {"position": "Top", "suit": "♣", "rank": "7"},  # partner discards ♣
                {"position": "Left", "suit": "♠", "rank": "8"},
            ]},
        ]
        result = read_partner("Top", [], tricks, "HOKUM", "♥")
        # ♣ should have negative strength (discarded → short)
        detail = result.get("detail", "")
        # The suit should show weakness — check via likely_strong_suits exclusion
        assert "♣" not in result["likely_strong_suits"]

    def test_partner_high_discard_exhausting(self):
        """Partner discards A♦ → notes mention exhausting."""
        tricks = [
            {"leader": "Bottom", "cards": [
                {"position": "Bottom", "suit": "♠", "rank": "A"},
                {"position": "Right", "suit": "♠", "rank": "K"},
                {"position": "Top", "suit": "♦", "rank": "A"},  # high discard
                {"position": "Left", "suit": "♠", "rank": "8"},
            ]},
        ]
        result = read_partner("Top", [], tricks, "HOKUM", "♥")
        assert "exhausting" in result["detail"]


# ═══════════════════════════════════════════════════════════════
#  PRO DATA CONSTANTS
# ═══════════════════════════════════════════════════════════════

class TestProDataTrumpTiming:
    """Verify trump timing constants from pro_data."""

    def test_trump_in_by_trick_exists(self):
        """TRUMP_IN_BY_TRICK should have entries for tricks 1-8."""
        for trick in range(1, 9):
            assert trick in TRUMP_IN_BY_TRICK

    def test_trump_in_declining_curve(self):
        """Trump-in rate should generally decline from trick 1 to trick 8."""
        assert TRUMP_IN_BY_TRICK[1] > TRUMP_IN_BY_TRICK[8]
        assert TRUMP_IN_BY_TRICK[1] > 0.40  # ~43%
        assert TRUMP_IN_BY_TRICK[8] < 0.20  # ~15.5%

    def test_singleton_lead_ranks_exist(self):
        """SINGLETON_LEAD_RANKS should have 10 and A entries."""
        assert "10" in SINGLETON_LEAD_RANKS
        assert "A" in SINGLETON_LEAD_RANKS
        assert SINGLETON_LEAD_RANKS["10"] > 0.10
        assert SINGLETON_LEAD_RANKS["A"] > 0.10
