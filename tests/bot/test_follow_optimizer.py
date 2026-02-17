"""Tests for follow_optimizer module."""
import pytest


class MockCard:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank}{self.suit}"


def _hand(specs: list[str]) -> list[MockCard]:
    """Build a hand from shorthand like ['A♠', 'K♥', '7♦']."""
    cards = []
    for s in specs:
        rank = s[:-1]
        suit = s[-1]
        cards.append(MockCard(rank, suit))
    return cards


from ai_worker.strategies.components.follow_optimizer import optimize_follow, _beats


class TestBeatsHelper:
    """Test the _beats rank comparison helper."""

    def test_ace_beats_king_sun(self):
        assert _beats("A", "K", "SUN") is True

    def test_king_does_not_beat_ace_sun(self):
        assert _beats("K", "A", "SUN") is False

    def test_jack_beats_nine_hokum(self):
        assert _beats("J", "9", "HOKUM") is True

    def test_nine_beats_ace_hokum(self):
        assert _beats("9", "A", "HOKUM") is True

    def test_ace_does_not_beat_nine_hokum(self):
        assert _beats("A", "9", "HOKUM") is False


class TestFollowOptimizer:
    """Follow-suit optimizer tests."""

    def test_dodge_when_partner_winning(self):
        """Play lowest card when partner is winning."""
        hand = _hand(["A♠", "K♠", "7♠"])
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "10", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=3, partner_winning=True, partner_card_index=0,
            trick_points=10, tricks_remaining=5, we_are_buyers=True,
        )
        assert result["tactic"] == "FEED_PARTNER"
        # Should feed A♠ (11 pts) to partner
        assert hand[result["card_index"]].rank == "A"

    def test_dodge_low_value_partner(self):
        """Play lowest when partner winning but no high-value to feed."""
        hand = _hand(["9♠", "8♠", "7♠"])
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "K", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=3, partner_winning=True, partner_card_index=0,
            trick_points=4, tricks_remaining=5, we_are_buyers=True,
        )
        assert result["tactic"] == "DODGE"
        assert hand[result["card_index"]].rank == "7"

    def test_win_big_high_value_trick(self):
        """Win with cheapest beater on high-value trick."""
        hand = _hand(["A♠", "K♠", "7♠"])
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "Q", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=3, partner_winning=False, partner_card_index=None,
            trick_points=18, tricks_remaining=4, we_are_buyers=True,
        )
        assert result["tactic"] == "WIN_BIG"
        # Should use cheapest beater (K beats Q)
        assert hand[result["card_index"]].rank == "K"

    def test_win_cheap_seat_4_guaranteed(self):
        """Seat 4 wins cheaply — guaranteed last player."""
        hand = _hand(["10♠", "K♠", "7♠"])
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[
                {"rank": "9", "suit": "♠"},
                {"rank": "8", "suit": "♠"},
                {"rank": "J", "suit": "♠"},
            ],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=4, partner_winning=False, partner_card_index=None,
            trick_points=4, tricks_remaining=3, we_are_buyers=True,
        )
        assert result["tactic"] == "WIN_CHEAP"
        assert hand[result["card_index"]].rank == "K"

    def test_shed_safe_cant_win(self):
        """Shed lowest value when can't beat current winner."""
        hand = _hand(["7♠", "8♠"])
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1],
            table_cards=[{"rank": "A", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=3, partner_winning=False, partner_card_index=None,
            trick_points=11, tricks_remaining=4, we_are_buyers=True,
        )
        assert result["tactic"] == "SHED_SAFE"
        assert hand[result["card_index"]].rank == "7"

    def test_trump_in_when_void(self):
        """Trump in when void in led suit and trick is valuable."""
        hand = _hand(["J♥", "7♥", "8♦"])  # void in ♠ (led suit)
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "A", "suit": "♠"}],
            led_suit="♠", mode="HOKUM", trump_suit="♥",
            seat=3, partner_winning=False, partner_card_index=None,
            trick_points=15, tricks_remaining=4, we_are_buyers=True,
        )
        assert result["tactic"] == "TRUMP_IN"
        assert hand[result["card_index"]].suit == "♥"
        # Use cheapest trump (7♥)
        assert hand[result["card_index"]].rank == "7"

    def test_trump_over_opponent(self):
        """Over-trump when opponent already trumped."""
        hand = _hand(["J♥", "9♥", "8♦"])
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[
                {"rank": "A", "suit": "♠"},
                {"rank": "10", "suit": "♥"},  # opponent trumped
            ],
            led_suit="♠", mode="HOKUM", trump_suit="♥",
            seat=4, partner_winning=False, partner_card_index=None,
            trick_points=21, tricks_remaining=3, we_are_buyers=True,
        )
        assert result["tactic"] == "TRUMP_OVER"
        # Must beat 10♥ with lowest trump that can (A♥ > 10♥ in HOKUM)
        assert hand[result["card_index"]].suit == "♥"

    def test_dodge_void_partner_winning(self):
        """When void and partner is winning, discard instead of trumping."""
        hand = _hand(["J♥", "7♦", "8♦"])
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "A", "suit": "♠"}],
            led_suit="♠", mode="HOKUM", trump_suit="♥",
            seat=3, partner_winning=True, partner_card_index=0,
            trick_points=11, tricks_remaining=4, we_are_buyers=True,
        )
        assert result["tactic"] == "DODGE"
        # Should NOT waste trump
        assert hand[result["card_index"]].suit != "♥"

    def test_single_legal_card(self):
        """Only one legal card — play it."""
        hand = _hand(["A♠", "K♥", "7♦"])
        result = optimize_follow(
            hand=hand, legal_indices=[0],
            table_cards=[{"rank": "10", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=2, partner_winning=False, partner_card_index=None,
            trick_points=10, tricks_remaining=5, we_are_buyers=True,
        )
        assert result["card_index"] == 0
        assert result["confidence"] == 1.0

    def test_no_legal_cards(self):
        """Edge case: no legal cards."""
        hand = _hand(["A♠"])
        result = optimize_follow(
            hand=hand, legal_indices=[],
            table_cards=[], led_suit="♠", mode="SUN",
            trump_suit=None, seat=2, partner_winning=False,
            partner_card_index=None, trick_points=0,
            tricks_remaining=8, we_are_buyers=True,
        )
        assert result["tactic"] == "SHED_SAFE"
        assert result["confidence"] == 0.0

    def test_hokum_rank_order(self):
        """J beats 9 which beats A in HOKUM mode."""
        hand = _hand(["J♠", "A♠"])
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1],
            table_cards=[{"rank": "9", "suit": "♠"}],
            led_suit="♠", mode="HOKUM", trump_suit="♠",
            seat=4, partner_winning=False, partner_card_index=None,
            trick_points=16, tricks_remaining=3, we_are_buyers=True,
        )
        assert result["tactic"] == "WIN_BIG"
        # HOKUM order: 7,8,Q,K,10,A,9,J — A(idx 5) < 9(idx 6) — A does NOT beat 9
        # Only J(idx 7) beats 9(idx 6)
        assert hand[result["card_index"]].rank == "J"

    def test_shed_void_creation(self):
        """When shedding, prefer creating voids (shortest suits)."""
        hand = _hand(["A♠", "7♥", "8♥", "9♦"])  # void in led suit ♣
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2, 3],
            table_cards=[{"rank": "K", "suit": "♣"}],
            led_suit="♣", mode="SUN", trump_suit=None,
            seat=2, partner_winning=False, partner_card_index=None,
            trick_points=4, tricks_remaining=5, we_are_buyers=True,
        )
        # Should discard from shortest non-trump suit
        assert result["tactic"] == "SHED_SAFE"


class TestProDataCalibration:
    """Tests verifying pro-data-calibrated follow-play behavior.

    Calibrated against 12,693 follow plays from 109 pro games:
    - Feed partner: 41.4% high (seat 4: 51.8%)
    - Conserve vs opponent: 23.0% high (seat 4: 19.3%)
    - Trump-in: only 26.8% when void
    - Second-hand-low: 42.7% early tricks
    """

    def test_feed_partner_seat4_higher_confidence(self):
        """Seat 4 should have higher confidence for feeding (pro: 51.8%)."""
        hand = _hand(["A♠", "K♠", "7♠"])
        result_s3 = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "10", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=3, partner_winning=True, partner_card_index=0,
            trick_points=10, tricks_remaining=5, we_are_buyers=True,
        )
        result_s4 = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "10", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=4, partner_winning=True, partner_card_index=0,
            trick_points=10, tricks_remaining=5, we_are_buyers=True,
        )
        assert result_s3["tactic"] == "FEED_PARTNER"
        assert result_s4["tactic"] == "FEED_PARTNER"
        # Seat 4 should be more confident (pro: 51.8% vs 39.1%)
        assert result_s4["confidence"] > result_s3["confidence"]

    def test_trump_threshold_raised_to_15(self):
        """Pro data: only 26.8% trump → require 15+ pts (was 10)."""
        hand = _hand(["7♥", "8♦"])  # trump=♥, void in ♠
        # 12 points on table — below new threshold of 15
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1],
            table_cards=[{"rank": "A", "suit": "♠"}],
            led_suit="♠", mode="HOKUM", trump_suit="♥",
            seat=3, partner_winning=False, partner_card_index=None,
            trick_points=12, tricks_remaining=4, we_are_buyers=True,
        )
        # Should NOT trump — save trump for higher-value tricks
        assert result["tactic"] == "SHED_SAFE"

    def test_trump_at_15_points(self):
        """Trump-in IS triggered at 15+ points even from seat 3."""
        hand = _hand(["7♥", "8♦"])  # trump=♥, void in ♠
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1],
            table_cards=[{"rank": "A", "suit": "♠"}, {"rank": "10", "suit": "♠"}],
            led_suit="♠", mode="HOKUM", trump_suit="♥",
            seat=3, partner_winning=False, partner_card_index=None,
            trick_points=21, tricks_remaining=4, we_are_buyers=True,
        )
        assert result["tactic"] == "TRUMP_IN"

    def test_trump_seat4_medium_trick(self):
        """Seat 4 can trump medium-value tricks (10-14 pts)."""
        hand = _hand(["7♥", "8♦"])  # trump=♥, void in ♠
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1],
            table_cards=[{"rank": "K", "suit": "♠"}, {"rank": "8", "suit": "♠"}, {"rank": "7", "suit": "♠"}],
            led_suit="♠", mode="HOKUM", trump_suit="♥",
            seat=4, partner_winning=False, partner_card_index=None,
            trick_points=12, tricks_remaining=4, we_are_buyers=True,
        )
        # Seat 4 can trump medium tricks (10-14)
        assert result["tactic"] == "TRUMP_IN"

    def test_second_hand_low_early_higher_confidence(self):
        """Early tricks should have higher second-hand-low confidence (pro: 42.7%)."""
        hand = _hand(["K♠", "8♠", "7♠"])
        # Early game (6 tricks remaining = trick 2-3)
        result_early = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "9", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=2, partner_winning=False, partner_card_index=None,
            trick_points=0, tricks_remaining=6, we_are_buyers=True,
        )
        # Late game (2 tricks remaining)
        result_late = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "9", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=2, partner_winning=False, partner_card_index=None,
            trick_points=0, tricks_remaining=2, we_are_buyers=True,
        )
        assert result_early["tactic"] == "SECOND_HAND_LOW"
        assert result_late["tactic"] == "SECOND_HAND_LOW"
        # Early tricks should have higher confidence
        assert result_early["confidence"] > result_late["confidence"]

    def test_seat4_desperation_late_higher_confidence(self):
        """Seat 4 desperation should be more confident in late game (pro: 23.8% vs 17.5%)."""
        hand = _hand(["K♠", "7♠"])
        # Late game
        result_late = optimize_follow(
            hand=hand, legal_indices=[0, 1],
            table_cards=[{"rank": "Q", "suit": "♠"}, {"rank": "8", "suit": "♠"}, {"rank": "9", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=4, partner_winning=False, partner_card_index=None,
            trick_points=12, tricks_remaining=2, we_are_buyers=True,
        )
        # Early game
        result_early = optimize_follow(
            hand=hand, legal_indices=[0, 1],
            table_cards=[{"rank": "Q", "suit": "♠"}, {"rank": "8", "suit": "♠"}, {"rank": "9", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=4, partner_winning=False, partner_card_index=None,
            trick_points=12, tricks_remaining=6, we_are_buyers=True,
        )
        assert result_late["tactic"] == "DESPERATION"
        assert result_early["tactic"] == "DESPERATION"
        # Late game should have higher confidence (pro: 23.8% vs 17.5%)
        assert result_late["confidence"] > result_early["confidence"]

    def test_feed_offsuit_partner_winning(self):
        """When void + partner winning, feed high cards (pro: 39.2%)."""
        hand = _hand(["A♦", "7♣", "8♣"])  # void in ♠
        result = optimize_follow(
            hand=hand, legal_indices=[0, 1, 2],
            table_cards=[{"rank": "K", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=3, partner_winning=True, partner_card_index=0,
            trick_points=4, tricks_remaining=5, we_are_buyers=True,
        )
        assert result["tactic"] == "FEED_OFFSUIT"
        assert hand[result["card_index"]].rank == "A"

    def test_feed_offsuit_seat4_higher_confidence(self):
        """Seat 4 feed off-suit should have higher confidence."""
        hand = _hand(["A♦", "7♣"])  # void in ♠
        result_s3 = optimize_follow(
            hand=hand, legal_indices=[0, 1],
            table_cards=[{"rank": "K", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=3, partner_winning=True, partner_card_index=0,
            trick_points=4, tricks_remaining=5, we_are_buyers=True,
        )
        result_s4 = optimize_follow(
            hand=hand, legal_indices=[0, 1],
            table_cards=[{"rank": "K", "suit": "♠"}],
            led_suit="♠", mode="SUN", trump_suit=None,
            seat=4, partner_winning=True, partner_card_index=0,
            trick_points=4, tricks_remaining=5, we_are_buyers=True,
        )
        assert result_s3["tactic"] == "FEED_OFFSUIT"
        assert result_s4["tactic"] == "FEED_OFFSUIT"
        assert result_s4["confidence"] > result_s3["confidence"]
