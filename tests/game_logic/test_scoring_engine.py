"""
Test Scoring Engine
Tests for ScoringEngine: card points, project scoring, Khasara, Kaboot,
tiebreaking, doubling multipliers, and end-to-end calculate_final_scores.
"""
import unittest
from unittest.mock import MagicMock, PropertyMock
from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.constants import GamePhase


class _ScoringTestBase(unittest.TestCase):
    """Shared helpers for scoring tests."""

    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p1", "Player 1")  # Index 0, Bottom, US
        self.game.add_player("p2", "Player 2")  # Index 1, Right, THEM
        self.game.add_player("p3", "Player 3")  # Index 2, Top, US
        self.game.add_player("p4", "Player 4")  # Index 3, Left, THEM
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        self.game.bid = {'bidder': 'Bottom', 'type': 'HOKUM', 'suit': '♠'}
        self.game.doubling_level = 1
        self.game.sawa_failed_khasara = False
        self.game.declarations = {}

    def _add_tricks(self, us_wins, them_wins, us_points_each=13, them_points_each=13):
        """Add simplified trick history."""
        self.game.round_history = []
        for _ in range(us_wins):
            self.game.round_history.append({'winner': 'Bottom', 'points': us_points_each})
        for _ in range(them_wins):
            self.game.round_history.append({'winner': 'Right', 'points': them_points_each})


class TestCardAbnat(_ScoringTestBase):
    """Tests for calculate_card_abnat — raw point tallying."""

    def test_basic_point_tallying(self):
        """Points from each trick should sum correctly per team."""
        self._add_tricks(us_wins=4, them_wins=4, us_points_each=15, them_points_each=10)
        us, them, bonus = self.game.scoring_engine.calculate_card_abnat()
        # 4*15 = 60 for US, 4*10 = 40 for THEM, plus last trick bonus to THEM (last trick is a THEM trick)
        self.assertEqual(us, 60)
        self.assertEqual(them, 40 + 10)  # +10 last trick bonus

    def test_last_trick_bonus_goes_to_winner(self):
        """The team that wins the last trick gets +10 bonus."""
        self._add_tricks(us_wins=1, them_wins=0, us_points_each=20)
        us, them, bonus = self.game.scoring_engine.calculate_card_abnat()
        self.assertEqual(bonus['us'], 10)
        self.assertEqual(bonus['them'], 0)
        self.assertEqual(us, 30)  # 20 + 10 bonus

    def test_empty_round_history(self):
        """No tricks played should produce zero points."""
        self.game.round_history = []
        us, them, bonus = self.game.scoring_engine.calculate_card_abnat()
        self.assertEqual(us, 0)
        self.assertEqual(them, 0)


class TestScoreCalculation(_ScoringTestBase):
    """Tests for rounding — validated against Kammelna formulas.

    SUN: floor-to-even → divmod(abnat, 5); q + (1 if q%2==1 and r>0)
    HOKUM: individual → divmod(abnat, 10); q + (1 if r>5)
    """

    def test_hokum_rounding_down(self):
        """HOKUM: remainder <= 5 rounds down."""
        se = self.game.scoring_engine
        self.assertEqual(se._calculate_score_for_team(65, 'HOKUM'), 6)

    def test_hokum_rounding_up(self):
        """HOKUM: remainder > 5 rounds up."""
        se = self.game.scoring_engine
        self.assertEqual(se._calculate_score_for_team(66, 'HOKUM'), 7)

    def test_sun_exact_multiple(self):
        """SUN: exact multiple of 5 → quotient directly."""
        se = self.game.scoring_engine
        # 65: divmod(65,5) = (13,0) → 13
        self.assertEqual(se._calculate_score_for_team(65, 'SUN'), 13)

    def test_sun_floor_to_even_even_quotient(self):
        """SUN: even quotient with remainder → stays (no round up)."""
        se = self.game.scoring_engine
        # 33: divmod(33,5) = (6,3) → q=6 (even), r>0 but even → 6
        self.assertEqual(se._calculate_score_for_team(33, 'SUN'), 6)

    def test_sun_floor_to_even_odd_quotient(self):
        """SUN: odd quotient with remainder → rounds up."""
        se = self.game.scoring_engine
        # 28: divmod(28,5) = (5,3) → q=5 (odd), r>0 → 5+1=6
        self.assertEqual(se._calculate_score_for_team(28, 'SUN'), 6)

    def test_sun_total_always_26(self):
        """SUN floor-to-even always sums to 26 when inputs sum to 130."""
        from game_engine.logic.scoring_engine import ScoringEngine
        for us in range(0, 131):
            them = 130 - us
            total = ScoringEngine.sun_card_gp(us) + ScoringEngine.sun_card_gp(them)
            self.assertEqual(total, 26, f"SUN: {us}+{them}=130 but GP sums to {total}")


class TestTiebreak(_ScoringTestBase):
    """Tests for calculate_game_points_with_tiebreak — Kammelna pair rounding."""

    def test_total_equals_16_hokum_valid_split(self):
        """HOKUM: pair-based rounding sums to 16 for valid 162-total."""
        se = self.game.scoring_engine
        # 86 card + 10 ardh = 96, 66 card + 0 ardh = 66 → total 162
        result = se.calculate_game_points_with_tiebreak(86, 66, 10, 0, 'us')
        total = result['game_points']['us'] + result['game_points']['them']
        self.assertEqual(total, 16)

    def test_hokum_pair_sum_constraint(self):
        """HOKUM pair-based rounding always sums to 16 for valid raw=162."""
        from game_engine.logic.scoring_engine import ScoringEngine
        for us in range(0, 163):
            them = 162 - us
            gp_us, gp_them = ScoringEngine.hokum_pair_gp(us, them)
            self.assertEqual(gp_us + gp_them, 16,
                             f"HOKUM: {us}+{them}=162 but GP sums to {gp_us + gp_them}")

    def test_tiebreak_winner_with_unequal_raw(self):
        """Team with more raw points wins."""
        se = self.game.scoring_engine
        result = se.calculate_game_points_with_tiebreak(80, 50, 10, 10, 'us')
        self.assertEqual(result['winner'], 'us')

    def test_tiebreak_equal_gp_bidder_wins(self):
        """When game points are exactly tied, bidder_team wins."""
        se = self.game.scoring_engine
        # 71+10=81, 71+10=81 → both round to 8 → tie → bidder wins
        result = se.calculate_game_points_with_tiebreak(71, 71, 10, 10, 'us')
        self.assertEqual(result['winner'], 'us')


class TestKaboot(_ScoringTestBase):
    """Tests for Kaboot (shutdown) scoring."""

    def test_kaboot_us_hokum(self):
        """US wins all tricks → 25 points in Hokum."""
        self._add_tricks(us_wins=8, them_wins=0, us_points_each=16)
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        self.assertEqual(score_us, 25, "Kaboot in Hokum should give 25 points")
        self.assertEqual(score_them, 0)
        self.assertTrue(result['us']['isKaboot'])

    def test_kaboot_them_sun(self):
        """THEM wins all tricks in Sun → 44 points."""
        self.game.game_mode = 'SUN'
        self.game.trump_suit = None
        self.game.bid = {'bidder': 'Right', 'type': 'SUN', 'suit': None}
        self._add_tricks(us_wins=0, them_wins=8, them_points_each=16)
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        self.assertEqual(score_them, 44, "Kaboot in Sun should give 44 points")
        self.assertTrue(result['them']['isKaboot'])


class TestKhasara(_ScoringTestBase):
    """Tests for Khasara (bidder team loses)."""

    def test_khasara_gives_all_points_to_opponent(self):
        """When bidder (us) scores less than opponent, all points transfer."""
        # US (bidder) wins few tricks, THEM wins most
        self._add_tricks(us_wins=2, them_wins=6, us_points_each=10, them_points_each=15)
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        # Bidder (us) loses → Khasara → all points go to them
        self.assertEqual(score_us, 0, "Bidder losing should get 0")
        self.assertGreater(score_them, 0, "Opponent should get all points on Khasara")

    def test_no_khasara_when_bidder_wins(self):
        """Bidder team winning should not trigger Khasara."""
        self._add_tricks(us_wins=6, them_wins=2, us_points_each=15, them_points_each=10)
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        self.assertGreater(score_us, 0)


class TestDoublingMultiplier(_ScoringTestBase):
    """Tests for doubling chain (double, triple, four, gahwa)."""

    def test_doubled_multiplies_by_2(self):
        """Doubling level 2 should multiply all scores by 2."""
        self.game.doubling_level = 2
        self._add_tricks(us_wins=6, them_wins=2, us_points_each=15, them_points_each=10)
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        self.assertEqual(result['us']['multiplierApplied'], 2)

    def test_gahwa_instant_win(self):
        """Gahwa (level 100+) with Kaboot gives 152 to the winning side."""
        self.game.doubling_level = 100
        # Kaboot: US wins ALL tricks, so one side has 0 → triggers 152 instant win
        self._add_tricks(us_wins=8, them_wins=0, us_points_each=16)
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        self.assertEqual(score_us, 152, "Gahwa + Kaboot should give 152")
        self.assertEqual(score_them, 0)


class TestGPOverflow(_ScoringTestBase):
    """Tests for GP pair-based rounding — Kammelna validated formulas."""

    def test_hokum_pair_handles_sum_17(self):
        """HOKUM: when individual rounding sums to 17, reduce larger remainder."""
        from game_engine.logic.scoring_engine import ScoringEngine
        # 86+76=162: individual → 9+8=17, raw_a%10=6 > raw_b%10=6 → reduce a
        gp_a, gp_b = ScoringEngine.hokum_pair_gp(86, 76)
        self.assertEqual(gp_a + gp_b, 16)

    def test_hokum_pair_handles_sum_15(self):
        """HOKUM: when individual rounding sums to 15, increase larger remainder."""
        from game_engine.logic.scoring_engine import ScoringEngine
        # 85+77=162: individual → 8+7=15, raw_a%10=5 > raw_b%10=7 → increase b
        gp_a, gp_b = ScoringEngine.hokum_pair_gp(85, 77)
        self.assertEqual(gp_a + gp_b, 16)

    def test_extreme_hokum_split(self):
        """HOKUM: extreme split should still produce valid GP."""
        from game_engine.logic.scoring_engine import ScoringEngine
        gp_a, gp_b = ScoringEngine.hokum_pair_gp(150, 12)
        self.assertGreaterEqual(gp_a, 0)
        self.assertGreaterEqual(gp_b, 0)
        self.assertEqual(gp_a + gp_b, 16)

    def test_sun_total_26_with_valid_split(self):
        """SUN: total GP should be 26 for valid 130-total raw."""
        self.game.game_mode = 'SUN'
        self.game.bid = {'bidder': 'Bottom', 'type': 'SUN', 'suit': None}
        se = self.game.scoring_engine
        # 58 card + 10 ardh = 68, 52 card + 10 ardh = 62 → total 130
        result = se.calculate_game_points_with_tiebreak(58, 52, 10, 10, 'us')
        total = result['game_points']['us'] + result['game_points']['them']
        self.assertEqual(total, 26, "Total GP must equal 26 in SUN")


class TestProjectIntegration(_ScoringTestBase):
    """Tests for projects integrated into final scoring."""

    def test_project_adds_game_points(self):
        """Projects should add abnat / 10 game points in Hokum."""
        # Bidder (US) must win the round for Khasara not to apply.
        # Give US more trick points so bidder wins.
        self._add_tricks(us_wins=6, them_wins=2, us_points_each=15, them_points_each=10)
        # Declare a SIRA (50 points) for US team
        self.game.declarations = {
            'Bottom': [{'type': 'SIRA', 'rank': 'Q', 'suit': '♥', 'score': 50}]
        }
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()
        self.assertEqual(result['us']['projectPoints'], 50)
        # 50 // 10 = 5 extra game points for US
        self.assertGreater(score_us, score_them)


if __name__ == '__main__':
    unittest.main()
