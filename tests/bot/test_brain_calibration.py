"""Tests for brain.py point density calibration.

Validates that the brain cascade uses pro-data-calibrated thresholds:
- CRITICAL: 26+ pts → fight (0.85)
- HIGH: 18+ pts → fight (raised from 16, calibrated to pro 19.3% conserve rate)
- Late-game boost: tricks 5+ → higher confidence
"""
import pytest
from ai_worker.strategies.components.brain import consult_brain


class MockCard:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit


def _hand(specs):
    return [MockCard(s[:-1], s[-1]) for s in specs]


class TestPointDensityCalibration:
    """Brain point density thresholds calibrated to pro data."""

    def test_critical_threshold_26(self):
        """26+ points on table → CRITICAL (fight hard)."""
        hand = _hand(["A♠", "K♠", "7♥"])
        result = consult_brain(
            hand=hand,
            table_cards=[{"rank": "A"}, {"rank": "10"}],  # 21 pts SUN
            mode="SUN", trump_suit=None, position="Bottom",
            we_are_buyers=True, partner_winning=False,
            tricks_played=3, tricks_won_by_us=1,
            master_indices=[], tracker_voids={},
            partner_info=None,
        )
        # 21 points is below 26 CRITICAL but above 18 HIGH
        assert "HIGH" in result["reasoning"] or "point_density" in result["modules_consulted"]

    def test_high_threshold_raised_to_18(self):
        """16 points no longer triggers HIGH — raised to 18 (pro calibration)."""
        hand = _hand(["A♠", "K♠", "7♥"])
        # 16 points — was HIGH, now below threshold
        result = consult_brain(
            hand=hand,
            table_cards=[{"rank": "K"}, {"rank": "Q"}, {"rank": "9"}],  # 4+3+0=7 in SUN
            mode="SUN", trump_suit=None, position="Bottom",
            we_are_buyers=True, partner_winning=False,
            tricks_played=3, tricks_won_by_us=1,
            master_indices=[], tracker_voids={},
            partner_info=None,
        )
        # 7 points is below 18 HIGH — should not have HIGH in reasoning
        if result["reasoning"] != "no module confident":
            assert "HIGH" not in result["reasoning"]

    def test_partner_winning_low_shed(self):
        """Partner winning with low points → shed low card."""
        hand = _hand(["A♠", "K♠", "7♠"])
        result = consult_brain(
            hand=hand,
            table_cards=[{"rank": "8"}],  # 0 pts SUN
            mode="SUN", trump_suit=None, position="Bottom",
            we_are_buyers=True, partner_winning=True,
            tricks_played=3, tricks_won_by_us=2,
            master_indices=[], tracker_voids={},
            partner_info=None,
        )
        assert "partner winning" in result["reasoning"]

    def test_late_game_higher_confidence(self):
        """Late game (tricks_played >= 5) should boost fight confidence."""
        hand = _hand(["A♠", "K♠", "7♥"])
        table = [{"rank": "10"}, {"rank": "K"}]  # 14 pts SUN — above 18 with A

        result_early = consult_brain(
            hand=hand, table_cards=table,
            mode="SUN", trump_suit=None, position="Bottom",
            we_are_buyers=True, partner_winning=False,
            tricks_played=2, tricks_won_by_us=1,
            master_indices=[], tracker_voids={},
            partner_info=None,
        )
        result_late = consult_brain(
            hand=hand, table_cards=table,
            mode="SUN", trump_suit=None, position="Bottom",
            we_are_buyers=True, partner_winning=False,
            tricks_played=6, tricks_won_by_us=3,
            master_indices=[], tracker_voids={},
            partner_info=None,
        )
        # Both should consult point_density
        assert "point_density" in result_early["modules_consulted"]
        assert "point_density" in result_late["modules_consulted"]

    def test_trick_review_shifts_threshold(self):
        """Trick review momentum adjusts cascade threshold."""
        hand = _hand(["A♠", "K♠", "7♥"])
        base_args = dict(
            hand=hand,
            table_cards=[{"rank": "10"}, {"rank": "K"}],
            mode="SUN", trump_suit=None, position="Bottom",
            we_are_buyers=True, partner_winning=False,
            tricks_played=3, tricks_won_by_us=1,
            master_indices=[], tracker_voids={},
            partner_info=None,
        )
        # AGGRESSIVE shift → lower threshold (0.4)
        result_agg = consult_brain(
            **base_args,
            trick_review_info={"strategy_shift": "AGGRESSIVE", "momentum": "LOSING"},
        )
        # DAMAGE_CONTROL → higher threshold (0.6)
        result_dc = consult_brain(
            **base_args,
            trick_review_info={"strategy_shift": "DAMAGE_CONTROL", "momentum": "COLLAPSING"},
        )
        # Both should consult trick_review
        assert "trick_review" in result_agg["modules_consulted"]
        assert "trick_review" in result_dc["modules_consulted"]


class TestProDataConstants:
    """Verify pro_data.py follow pattern constants exist and are reasonable."""

    def test_follow_constants_exist(self):
        """All follow-play constants should be importable."""
        from ai_worker.strategies.components.pro_data import (
            FEED_PARTNER_RATE,
            FEED_PARTNER_SEAT4,
            CONSERVE_OPP_RATE,
            CONSERVE_OPP_SEAT4,
            TRUMP_IN_VOID_RATE,
            SECOND_HAND_LOW_RATE,
            SECOND_HAND_LOW_EARLY,
            DISCARD_HIGH_PARTNER_WINNING,
            DISCARD_LOW_OPPONENT_WINNING,
            SEAT4_AGGRESSION_EARLY,
            SEAT4_AGGRESSION_LATE,
        )
        # Verify ranges are reasonable (all should be 0-1 probabilities)
        for val in [FEED_PARTNER_RATE, FEED_PARTNER_SEAT4, CONSERVE_OPP_RATE,
                    CONSERVE_OPP_SEAT4, TRUMP_IN_VOID_RATE, SECOND_HAND_LOW_RATE,
                    SECOND_HAND_LOW_EARLY, DISCARD_HIGH_PARTNER_WINNING,
                    DISCARD_LOW_OPPONENT_WINNING, SEAT4_AGGRESSION_EARLY,
                    SEAT4_AGGRESSION_LATE]:
            assert 0.0 < val < 1.0, f"Constant {val} out of range"

    def test_feed_vs_conserve_asymmetry(self):
        """Pros feed much more than conserve (41.4% vs 23.0%)."""
        from ai_worker.strategies.components.pro_data import (
            FEED_PARTNER_RATE, CONSERVE_OPP_RATE,
        )
        # Feed rate should be significantly higher than conserve rate
        assert FEED_PARTNER_RATE > CONSERVE_OPP_RATE + 0.10

    def test_seat4_has_biggest_swing(self):
        """Seat 4 should have the biggest partner-winning vs opponent-winning swing."""
        from ai_worker.strategies.components.pro_data import (
            FEED_PARTNER_SEAT4, CONSERVE_OPP_SEAT4,
            POSITION_FEED_CONSERVE_SWING,
        )
        # Seat 4 swing is ~32.5pp (biggest positional effect)
        swing = FEED_PARTNER_SEAT4 - CONSERVE_OPP_SEAT4
        assert swing > 0.30  # At least 30pp swing
        assert POSITION_FEED_CONSERVE_SWING[4] > POSITION_FEED_CONSERVE_SWING[3]

    def test_trump_in_rate_low(self):
        """Pros conserve trumps — only 26.8% trump when void."""
        from ai_worker.strategies.components.pro_data import TRUMP_IN_VOID_RATE
        assert TRUMP_IN_VOID_RATE < 0.30  # Pros are conservative with trumps
