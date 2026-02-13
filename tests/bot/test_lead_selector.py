"""Tests for lead_selector module."""
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


from ai_worker.strategies.components.lead_selector import select_lead


class TestLeadSelector:
    """Unified lead-card selection tests."""

    def test_master_cash_from_shortest_suit(self):
        """Lead master card from shortest suit."""
        hand = _hand(["A♠", "K♠", "10♠", "A♥", "7♦"])
        # A♠ master (idx 0), A♥ master (idx 3)
        # ♥ has 1 card (shorter), ♠ has 3 cards
        result = select_lead(
            hand=hand, mode="SUN", trump_suit=None,
            we_are_buyers=True, tricks_played=0, tricks_won_by_us=0,
            master_indices=[0, 3], partner_info=None,
            defense_info=None, trump_info=None, opponent_voids={},
        )
        assert result["strategy"] == "MASTER_CASH"
        assert result["card_index"] == 3  # A♥ from shorter suit
        assert result["confidence"] >= 0.8

    def test_master_skips_voided_suit(self):
        """Don't lead master in a suit opponents are void in."""
        hand = _hand(["A♠", "K♥", "7♦"])
        result = select_lead(
            hand=hand, mode="SUN", trump_suit=None,
            we_are_buyers=True, tricks_played=0, tricks_won_by_us=0,
            master_indices=[0], partner_info=None,
            defense_info=None, trump_info=None,
            opponent_voids={"♠": {"Right"}},  # opponent void in ♠
        )
        # A♠ is master but ♠ voided → should fall through to SAFE_LEAD
        assert result["strategy"] != "MASTER_CASH" or result["card_index"] != 0

    def test_trump_draw_hokum_j9(self):
        """Lead high trump when trump_info says DRAW."""
        hand = _hand(["J♠", "9♠", "A♠", "7♥", "8♦"])
        result = select_lead(
            hand=hand, mode="HOKUM", trump_suit="♠",
            we_are_buyers=True, tricks_played=1, tricks_won_by_us=1,
            master_indices=[], partner_info=None,
            defense_info=None,
            trump_info={"action": "DRAW", "lead_trump": True},
            opponent_voids={},
        )
        assert result["strategy"] == "TRUMP_DRAW"
        assert hand[result["card_index"]].suit == "♠"

    def test_partner_feed(self):
        """Lead low in partner's strong suit."""
        hand = _hand(["7♥", "K♥", "A♠", "8♦"])
        result = select_lead(
            hand=hand, mode="SUN", trump_suit=None,
            we_are_buyers=True, tricks_played=2, tricks_won_by_us=1,
            master_indices=[], partner_info={
                "likely_strong_suits": ["♥"],
                "likely_void_suits": [],
                "confidence": 0.6,
            },
            defense_info=None, trump_info=None, opponent_voids={},
        )
        assert result["strategy"] == "PARTNER_FEED"
        assert hand[result["card_index"]].suit == "♥"
        # Should lead low card to let partner win
        assert hand[result["card_index"]].rank == "7"

    def test_defense_priority(self):
        """Follow defense_plan guidance when defending."""
        hand = _hand(["A♠", "K♠", "7♥", "8♦"])
        result = select_lead(
            hand=hand, mode="SUN", trump_suit=None,
            we_are_buyers=False, tricks_played=2, tricks_won_by_us=0,
            master_indices=[], partner_info=None,
            defense_info={
                "strategy": "ACTIVE",
                "priority_suit": "♠",
                "avoid_suit": "♦",
                "reasoning": "2A→attack",
            },
            trump_info=None, opponent_voids={},
        )
        assert result["strategy"] == "DEFENSE_PRIORITY"
        assert hand[result["card_index"]].suit == "♠"

    def test_long_run(self):
        """Lead from 4+ card suit."""
        hand = _hand(["A♥", "K♥", "10♥", "Q♥", "7♠"])
        result = select_lead(
            hand=hand, mode="SUN", trump_suit=None,
            we_are_buyers=True, tricks_played=1, tricks_won_by_us=0,
            master_indices=[], partner_info=None,
            defense_info=None, trump_info=None, opponent_voids={},
        )
        assert result["strategy"] == "LONG_RUN"
        assert hand[result["card_index"]].suit == "♥"

    def test_desperation_late_game(self):
        """Desperation when losing late in the game."""
        hand = _hand(["K♠", "7♥"])
        result = select_lead(
            hand=hand, mode="SUN", trump_suit=None,
            we_are_buyers=True, tricks_played=6, tricks_won_by_us=1,
            master_indices=[], partner_info=None,
            defense_info=None, trump_info=None, opponent_voids={},
        )
        assert result["strategy"] == "DESPERATION"

    def test_safe_lead_fallback(self):
        """Safe lead when no strong strategy applies."""
        hand = _hand(["7♠", "8♥", "9♦"])
        result = select_lead(
            hand=hand, mode="SUN", trump_suit=None,
            we_are_buyers=True, tricks_played=2, tricks_won_by_us=1,
            master_indices=[], partner_info=None,
            defense_info=None, trump_info=None, opponent_voids={},
        )
        assert result["strategy"] == "SAFE_LEAD"
        assert result["confidence"] > 0

    def test_empty_hand(self):
        """Edge case: empty hand."""
        result = select_lead(
            hand=[], mode="SUN", trump_suit=None,
            we_are_buyers=True, tricks_played=0, tricks_won_by_us=0,
            master_indices=[], partner_info=None,
            defense_info=None, trump_info=None, opponent_voids={},
        )
        assert result["strategy"] == "SAFE_LEAD"
        assert result["confidence"] == 0.0

    def test_none_info_dicts(self):
        """Works when all info dicts are None."""
        hand = _hand(["A♠", "K♥", "7♦"])
        result = select_lead(
            hand=hand, mode="HOKUM", trump_suit="♠",
            we_are_buyers=True, tricks_played=0, tricks_won_by_us=0,
            master_indices=[], partner_info=None,
            defense_info=None, trump_info=None, opponent_voids={},
        )
        assert "card_index" in result
        assert "strategy" in result
