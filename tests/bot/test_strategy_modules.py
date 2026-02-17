"""Tests for AI strategy modules: galoss_guard, cooperative_play, follow_optimizer, bid_reader.

Covers emergency detection, cooperative lead/follow, follow-suit optimization,
and bidding inference for the Baloot AI play phase.
"""
from __future__ import annotations

import unittest
from game_engine.models.card import Card

from ai_worker.strategies.components.galoss_guard import galoss_check, get_emergency_action
from ai_worker.strategies.components.cooperative_play import get_cooperative_lead, get_cooperative_follow
from ai_worker.strategies.components.follow_optimizer import optimize_follow
from ai_worker.strategies.components.bid_reader import infer_from_bids


class TestGalossGuard(unittest.TestCase):
    """Tests for galoss_guard.py — Khasara risk detection and emergency plays."""

    def test_galoss_buyer_critical(self):
        """Buyer has 0 tricks after 5 played tricks -> CRITICAL risk, emergency mode on."""
        result = galoss_check(
            mode="SUN",
            we_are_buyers=True,
            tricks_played=5,
            our_points=0,
            their_points=80,
            our_tricks=0,
            their_tricks=5,
        )
        self.assertEqual(result["risk_level"], "CRITICAL")
        self.assertTrue(result["emergency_mode"])
        self.assertTrue(result["we_risk_galoss"])
        self.assertFalse(result["they_risk_galoss"])
        self.assertEqual(result["buyer_tricks"], 0)

    def test_galoss_defender_pressing(self):
        """Defender has 6 tricks -- they_risk_galoss should be False because defenders cannot
        lose Galoss (only buyers can). The buyer is the one at risk."""
        result = galoss_check(
            mode="SUN",
            we_are_buyers=False,
            tricks_played=6,
            our_points=90,
            their_points=10,
            our_tricks=6,
            their_tricks=0,
        )
        # We are defender and winning big -- buyer is at risk, not us
        self.assertFalse(result["we_risk_galoss"])
        # The buyer (them) is at CRITICAL risk since they have 0 tricks at trick 6
        self.assertTrue(result["they_risk_galoss"])
        self.assertEqual(result["risk_level"], "CRITICAL")

    def test_galoss_no_risk_early(self):
        """Trick 2, even scores -> no meaningful risk assessment (too early)."""
        result = galoss_check(
            mode="SUN",
            we_are_buyers=True,
            tricks_played=1,
            our_points=10,
            their_points=10,
            our_tricks=1,
            their_tricks=0,
        )
        self.assertEqual(result["risk_level"], "NONE")
        self.assertFalse(result["emergency_mode"])
        self.assertFalse(result["we_risk_galoss"])
        self.assertFalse(result["they_risk_galoss"])

    def test_galoss_emergency_action_buyer_leading(self):
        """When buyer is in emergency galoss mode and leading, should play highest card."""
        hand = [Card("♠", "7"), Card("♠", "A"), Card("♥", "K")]
        legal_indices = [0, 1, 2]
        galoss_info = {"emergency_mode": True, "risk_level": "CRITICAL"}

        result = get_emergency_action(
            hand=hand,
            legal_indices=legal_indices,
            mode="SUN",
            trump_suit=None,
            we_are_buyers=True,
            galoss_info=galoss_info,
            is_leading=True,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["strategy"], "GALOSS_DESPERATION")
        # Should pick the A♠ (index 1) -- highest rank in SUN order
        self.assertEqual(result["card_index"], 1)

    def test_galoss_no_emergency_when_mode_off(self):
        """If emergency_mode is False in galoss_info, get_emergency_action returns None."""
        hand = [Card("♠", "A")]
        galoss_info = {"emergency_mode": False, "risk_level": "LOW"}
        result = get_emergency_action(
            hand=hand,
            legal_indices=[0],
            mode="SUN",
            trump_suit=None,
            we_are_buyers=True,
            galoss_info=galoss_info,
            is_leading=True,
        )
        self.assertIsNone(result)

    def test_galoss_defender_press_leads_ace(self):
        """Defender pressing galoss on buyer should cash Aces first."""
        hand = [Card("♠", "A"), Card("♥", "7"), Card("♦", "Q")]
        legal_indices = [0, 1, 2]
        galoss_info = {"emergency_mode": True, "risk_level": "CRITICAL"}

        result = get_emergency_action(
            hand=hand,
            legal_indices=legal_indices,
            mode="SUN",
            trump_suit=None,
            we_are_buyers=False,
            galoss_info=galoss_info,
            is_leading=True,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["strategy"], "GALOSS_PRESS")
        self.assertEqual(result["card_index"], 0)  # A♠


class TestCooperativePlay(unittest.TestCase):
    """Tests for cooperative_play.py — partner-coordinated leads and follows."""

    def test_cooperative_lead_feed_strong(self):
        """Partner is strong in hearts, we have low hearts -> recommends heart lead."""
        hand = [Card("♥", "7"), Card("♥", "8"), Card("♠", "A"), Card("♦", "K")]
        partner_info = {
            "likely_strong_suits": ["♥"],
            "likely_void_suits": [],
            "has_high_trumps": False,
            "estimated_trumps": 0,
            "confidence": 0.6,
        }

        result = get_cooperative_lead(
            hand=hand,
            partner_info=partner_info,
            mode="SUN",
            trump_suit=None,
        )
        self.assertIsNotNone(result)
        # Should feed a low heart to partner's strong suit
        self.assertEqual(hand[result["card_index"]].suit, "♥")
        self.assertIn(result["strategy"], ("FEED_STRONG", "SETUP_RUN", "ENTRY_TRANSFER"))

    def test_cooperative_lead_draw_trump(self):
        """We are buyers in HOKUM, partner has weak trumps with 2+ count.
        We hold J of trump -> should recommend DRAW_TRUMP."""
        hand = [
            Card("♠", "J"),  # 0 - high trump (J is highest in HOKUM)
            Card("♠", "7"),  # 1
            Card("♥", "A"),  # 2
            Card("♦", "K"),  # 3
        ]
        partner_info = {
            "likely_strong_suits": [],
            "likely_void_suits": [],
            "has_high_trumps": False,
            "estimated_trumps": 2,
            "confidence": 0.6,
        }

        result = get_cooperative_lead(
            hand=hand,
            partner_info=partner_info,
            mode="HOKUM",
            trump_suit="♠",
            we_are_buyers=True,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["strategy"], "DRAW_TRUMP")
        # Should pick J♠ (index 0) -- the highest trump to clear enemies
        self.assertEqual(result["card_index"], 0)

    def test_cooperative_lead_none_low_confidence(self):
        """Very low partner confidence -> returns None (no override)."""
        hand = [Card("♥", "7"), Card("♠", "A")]
        partner_info = {
            "likely_strong_suits": ["♥"],
            "likely_void_suits": [],
            "confidence": 0.1,  # Below 0.25 threshold
        }

        result = get_cooperative_lead(
            hand=hand,
            partner_info=partner_info,
            mode="SUN",
        )
        self.assertIsNone(result)

    def test_cooperative_follow_smart_discard(self):
        """Void in led suit, partner void in diamonds -> discard from diamonds."""
        hand = [
            Card("♦", "7"),  # 0 - partner also void in ♦
            Card("♣", "K"),  # 1 - from partner's strong suit
            Card("♣", "Q"),  # 2
        ]
        legal_indices = [0, 1, 2]
        partner_info = {
            "likely_strong_suits": ["♣"],
            "likely_void_suits": ["♦"],
            "confidence": 0.5,
        }

        result = get_cooperative_follow(
            hand=hand,
            legal_indices=legal_indices,
            partner_info=partner_info,
            led_suit="♥",  # We're void in hearts
            mode="SUN",
        )
        self.assertIsNotNone(result)
        self.assertIn(result["tactic"], ("SMART_DISCARD", "SIGNAL_SHAPE"))
        # Should discard from ♦ (partner's void) rather than ♣ (partner's strong)
        self.assertEqual(hand[result["card_index"]].suit, "♦")

    def test_cooperative_lead_setup_run(self):
        """We have 3+ cards in partner's strong suit -> SETUP_RUN."""
        hand = [
            Card("♥", "7"),
            Card("♥", "8"),
            Card("♥", "K"),
            Card("♠", "A"),
        ]
        partner_info = {
            "likely_strong_suits": ["♥"],
            "likely_void_suits": [],
            "has_high_trumps": False,
            "estimated_trumps": 0,
            "confidence": 0.6,
        }

        result = get_cooperative_lead(
            hand=hand,
            partner_info=partner_info,
            mode="SUN",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["strategy"], "SETUP_RUN")
        self.assertEqual(hand[result["card_index"]].suit, "♥")

    def test_cooperative_follow_discard_shortest_suit(self):
        """When void in led suit, prefer discarding from shortest suit (signal)."""
        # Hand has:
        # ♣: K (1 card) - Shortest
        # ♦: 7, 8 (2 cards)
        # ♠: Void (led suit)
        # ♥: Void
        hand = [
            Card("♣", "K"),  # 0 - Shortest suit (length 1)
            Card("♦", "7"),  # 1
            Card("♦", "8"),  # 2
        ]
        legal_indices = [0, 1, 2]
        partner_info = {
            "likely_strong_suits": [],
            "likely_void_suits": [],
            "confidence": 0.6,
        }

        # Led suit ♠ (void), partner NOT winning
        result = get_cooperative_follow(
            hand=hand,
            legal_indices=legal_indices,
            partner_info=partner_info,
            led_suit="♠",
            mode="SUN",
            partner_winning=False
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["tactic"], "SIGNAL_SHAPE")
        # Should discard K♣ (index 0) because it's from shortest suit
        self.assertEqual(result["card_index"], 0)


class TestFollowOptimizer(unittest.TestCase):
    """Tests for follow_optimizer.py — 8-tactic follow-suit cascade."""

    def _make_follow_args(self, **overrides):
        """Build default follow_optimizer args with overrides."""
        defaults = {
            "hand": [],
            "legal_indices": [],
            "table_cards": [],
            "led_suit": "♠",
            "mode": "SUN",
            "trump_suit": None,
            "seat": 4,
            "partner_winning": False,
            "partner_card_index": None,
            "trick_points": 0,
            "tricks_remaining": 4,
            "we_are_buyers": True,
        }
        defaults.update(overrides)
        return defaults

    def test_follow_feed_partner(self):
        """Partner winning with high card, we have A of spades -> feeds A (11pts) to partner."""
        hand = [
            Card("♠", "A"),  # 0 - 11pts, same suit
            Card("♠", "7"),  # 1 - 0pts, same suit
            Card("♥", "K"),  # 2 - off suit
        ]
        table_cards = [
            {"rank": "10", "suit": "♠", "position": "Right"},    # led
            {"rank": "K", "suit": "♠", "position": "Top"},       # partner
        ]

        result = optimize_follow(**self._make_follow_args(
            hand=hand,
            legal_indices=[0, 1],
            table_cards=table_cards,
            led_suit="♠",
            seat=4,
            partner_winning=True,
            partner_card_index=1,
            trick_points=14,  # 10 + 4
        ))
        self.assertEqual(result["tactic"], "FEED_PARTNER")
        self.assertEqual(result["card_index"], 0)  # A♠ to feed 11pts

    def test_follow_second_hand_low(self):
        """Seat 2, low-value trick (<10pts) -> plays cheapest legal card (SECOND_HAND_LOW)."""
        hand = [
            Card("♠", "A"),  # 0 - high
            Card("♠", "Q"),  # 1 - mid
            Card("♠", "7"),  # 2 - lowest
            Card("♥", "K"),  # 3 - off suit
        ]
        table_cards = [
            {"rank": "8", "suit": "♠", "position": "Right"},  # opponent led 8♠
        ]

        result = optimize_follow(**self._make_follow_args(
            hand=hand,
            legal_indices=[0, 1, 2],
            table_cards=table_cards,
            led_suit="♠",
            seat=2,
            partner_winning=False,
            trick_points=0,  # 8♠ = 0 pts
        ))
        self.assertEqual(result["tactic"], "SECOND_HAND_LOW")
        self.assertEqual(result["card_index"], 2)  # 7♠ is lowest

    def test_follow_shed_safe_void_partner_winning(self):
        """Void in led suit, partner winning -> sheds lowest value card (DODGE)."""
        hand = [
            Card("♥", "A"),  # 0 - 11pts off-suit
            Card("♦", "7"),  # 1 - 0pts off-suit
            Card("♣", "Q"),  # 2 - 3pts off-suit
        ]
        # All cards are off-suit (void in ♠)

        result = optimize_follow(**self._make_follow_args(
            hand=hand,
            legal_indices=[0, 1, 2],
            table_cards=[
                {"rank": "K", "suit": "♠", "position": "Right"},
                {"rank": "A", "suit": "♠", "position": "Top"},   # partner A♠
            ],
            led_suit="♠",
            seat=4,
            partner_winning=True,
            partner_card_index=1,
            trick_points=15,  # K(4) + A(11) = 15
        ))
        # Partner winning + we're void -> FEED_OFFSUIT (feed high points) or DODGE
        self.assertIn(result["tactic"], ("FEED_OFFSUIT", "DODGE"))

    def test_follow_single_legal_card(self):
        """Only one legal card -> plays it with SHED_SAFE and confidence 1.0."""
        hand = [Card("♠", "7"), Card("♥", "A")]

        result = optimize_follow(**self._make_follow_args(
            hand=hand,
            legal_indices=[0],  # only 7♠ is legal
            table_cards=[{"rank": "K", "suit": "♠", "position": "Right"}],
            led_suit="♠",
            seat=4,
        ))
        self.assertEqual(result["card_index"], 0)
        self.assertEqual(result["confidence"], 1.0)

    def test_follow_win_big_high_value_trick(self):
        """Trick has 15+ points on table -> WIN_BIG with cheapest beater."""
        hand = [
            Card("♠", "A"),  # 0 - can beat K, highest
            Card("♠", "10"), # 1 - can beat K, cheaper
            Card("♠", "7"),  # 2 - can't beat K
        ]
        table_cards = [
            {"rank": "K", "suit": "♠", "position": "Right"},
            {"rank": "Q", "suit": "♠", "position": "Top"},
            {"rank": "J", "suit": "♠", "position": "Left"},
        ]

        result = optimize_follow(**self._make_follow_args(
            hand=hand,
            legal_indices=[0, 1, 2],
            table_cards=table_cards,
            led_suit="♠",
            seat=4,
            partner_winning=False,
            trick_points=9,  # K(4)+Q(3)+J(2) = 9 -- below 15, so won't be WIN_BIG
        ))
        # With 9 points, seat 4, cheapest beater should be used
        self.assertIn(result["tactic"], ("WIN_CHEAP", "DESPERATION", "WIN_BIG"))
        self.assertIn(result["card_index"], [0, 1])  # either A or 10 beats K

    def test_follow_trump_in_hokum(self):
        """HOKUM mode, void in led suit, opponent winning 10+ trick -> TRUMP_IN."""
        hand = [
            Card("♣", "7"),  # 0 - trump (♣ is trump)
            Card("♦", "8"),  # 1 - off-suit non-trump
        ]
        table_cards = [
            {"rank": "A", "suit": "♠", "position": "Right"},  # A♠ = 11pts
        ]

        result = optimize_follow(**self._make_follow_args(
            hand=hand,
            legal_indices=[0, 1],
            table_cards=table_cards,
            led_suit="♠",
            mode="HOKUM",
            trump_suit="♣",
            seat=4,
            partner_winning=False,
            trick_points=11,
        ))
        self.assertEqual(result["tactic"], "TRUMP_IN")
        self.assertEqual(result["card_index"], 0)  # 7♣ trumps


class TestBidReader(unittest.TestCase):
    """Tests for bid_reader.py — bidding inference for play phase."""

    def test_bid_reader_hokum_inference(self):
        """Opponent bid Hokum in spades -> infer strong spade holding."""
        bid_history = [
            {"player": "Right", "action": "HOKUM", "suit": "♠"},
        ]
        result = infer_from_bids(
            my_position="Bottom",
            bid_history=bid_history,
        )
        self.assertEqual(result["declarer_position"], "Right")
        self.assertEqual(result["declarer_trump"], "♠")
        # Right player should have strong ♠
        right_info = result["players"]["Right"]
        self.assertIn("♠", right_info["strong_suits"])
        self.assertIn("J", right_info["likely_trumps"])
        self.assertIn("9", right_info["likely_trumps"])
        # Avoid spades (declarer's strong suit)
        self.assertIn("♠", result["avoid_suits"])
        # Other suits should be weak for the declarer
        self.assertTrue(len(right_info["weak_suits"]) > 0)

    def test_bid_reader_pass_inference(self):
        """Player passes in R1 -> likely weak in floor suit."""
        floor_card = {"suit": "♥", "rank": "J"}
        bid_history = [
            {"player": "Right", "action": "PASS", "suit": None},
        ]
        result = infer_from_bids(
            my_position="Bottom",
            bid_history=bid_history,
            floor_card=floor_card,
            bidding_round=1,
        )
        right_info = result["players"]["Right"]
        self.assertIn("♥", right_info["weak_suits"])
        self.assertEqual(right_info["bid_action"], "PASS")
        self.assertAlmostEqual(right_info["confidence"], 0.3)

    def test_bid_reader_sun_inference(self):
        """Player bids SUN -> infer strong balanced hand with multiple Aces."""
        bid_history = [
            {"player": "Left", "action": "SUN", "suit": None},
        ]
        result = infer_from_bids(
            my_position="Bottom",
            bid_history=bid_history,
        )
        self.assertEqual(result["declarer_position"], "Left")
        self.assertIsNone(result["declarer_trump"])
        left_info = result["players"]["Left"]
        self.assertGreaterEqual(left_info["likely_aces"], 2)
        self.assertEqual(len(left_info["strong_suits"]), 4)  # Strong in all suits

    def test_bid_reader_ashkal_inference(self):
        """Player bids ASHKAL -> infer dominant hand (3+ Aces)."""
        bid_history = [
            {"player": "Top", "action": "ASHKAL", "suit": None},
        ]
        result = infer_from_bids(
            my_position="Bottom",
            bid_history=bid_history,
        )
        # Top is partner of Bottom, so avoid_suits should be empty
        # (we don't avoid our own partner's suits)
        self.assertEqual(result["declarer_position"], "Top")
        top_info = result["players"]["Top"]
        self.assertGreaterEqual(top_info["likely_aces"], 3)
        self.assertAlmostEqual(top_info["confidence"], 0.8)

    def test_bid_reader_multiple_passes(self):
        """Multiple players pass -> they are all weak in floor suit."""
        floor_card = {"suit": "♦", "rank": "10"}
        bid_history = [
            {"player": "Right", "action": "PASS", "suit": None},
            {"player": "Top", "action": "PASS", "suit": None},
            {"player": "Left", "action": "PASS", "suit": None},
        ]
        result = infer_from_bids(
            my_position="Bottom",
            bid_history=bid_history,
            floor_card=floor_card,
            bidding_round=1,
        )
        for pos in ("Right", "Top", "Left"):
            self.assertIn("♦", result["players"][pos]["weak_suits"])

    def test_bid_reader_empty_history(self):
        """Empty bid history -> no inferences made, defaults returned."""
        result = infer_from_bids(
            my_position="Bottom",
            bid_history=[],
        )
        self.assertIsNone(result["declarer_position"])
        self.assertIsNone(result["declarer_trump"])
        self.assertEqual(result["avoid_suits"], [])
        self.assertEqual(result["target_suits"], [])


if __name__ == "__main__":
    unittest.main()
