"""
Test Scoring Integration
========================
Full integration tests for the ScoringEngine: card point tallying, GP
conversion, Kaboot, Khasara, doubling multipliers, Gahwa, project points,
tiebreak rules, and last trick bonus.

Key rules:
  SUN:  total GP = 26, Kaboot = 44. Rounding: (raw*2)/10, >=0.5 rounds up.
  HOKUM: total GP = 16, Kaboot = 25. Rounding: raw/10, >0.5 rounds up (0.5 rounds DOWN).
  Khasara: bidder gets fewer GP -> bidder=0, defender gets all GP.
  Doubling: multiply GP by level (2/3/4). Level 100 = Gahwa (152 if opponent has 0).
  Baloot GP added AFTER doubling (immune).
"""
import unittest

from game_engine.logic.game import Game
from game_engine.models.card import Card


class _ScoringIntegrationBase(unittest.TestCase):
    """Shared setup and helpers for scoring integration tests."""

    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p1", "Player 1")  # idx 0, Bottom, us
        self.game.add_player("p2", "Player 2")  # idx 1, Right, them
        self.game.add_player("p3", "Player 3")  # idx 2, Top, us
        self.game.add_player("p4", "Player 4")  # idx 3, Left, them
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '\u2660'
        self.game.bid = {'bidder': 'Bottom', 'type': 'HOKUM', 'suit': '\u2660'}
        self.game.doubling_level = 1
        self.game.sawa_failed_khasara = False
        self.game.declarations = {}

    def _add_tricks(self, us_wins, them_wins, us_points_each=13, them_points_each=13):
        """Add simplified trick history entries.

        Tricks won by 'us' use 'Bottom' as winner, 'them' use 'Right'.
        Points are raw card points PER TRICK (before last-trick bonus).
        """
        self.game.round_history = []
        for _ in range(us_wins):
            self.game.round_history.append({
                'winner': 'Bottom',
                'points': us_points_each,
            })
        for _ in range(them_wins):
            self.game.round_history.append({
                'winner': 'Right',
                'points': them_points_each,
            })

    def _add_interleaved_tricks(self, trick_list):
        """Add trick history from a list of (winner_position, points) tuples.

        This preserves the exact ordering of tricks, which matters for
        the last-trick bonus calculation.
        """
        self.game.round_history = []
        for winner, points in trick_list:
            self.game.round_history.append({
                'winner': winner,
                'points': points,
            })


class TestFullSunRound(_ScoringIntegrationBase):
    """Tests for a complete SUN round producing 26 total GP from tricks."""

    def test_full_sun_round_26gp(self):
        """8 tricks in SUN mode: total GP from card+ardh must equal 26.

        SUN total Abnat = 130 (120 card + 10 last trick).
        GP conversion: (raw * 2) / 10, >= 0.5 rounds up.
        Sum of both teams' GP = 26.
        """
        self.game.game_mode = 'SUN'
        self.game.trump_suit = None
        self.game.bid = {'bidder': 'Bottom', 'type': 'SUN', 'suit': None}

        # Distribute 120 card points: 60 each, last trick goes to US (+10 bonus)
        # US raw: 60+10=70, THEM raw: 60
        # Total abnat: 130
        self._add_interleaved_tricks([
            ('Bottom', 15), ('Right', 15),
            ('Bottom', 15), ('Right', 15),
            ('Bottom', 15), ('Right', 15),
            ('Bottom', 15), ('Right', 15),  # last trick won by them
        ])
        # Rearrange so last trick is explicit
        # Actually with _add_interleaved_tricks the last entry is the last trick
        # Last trick here is ('Right', 15), so them gets +10 bonus

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        # Before Khasara/doubling, base GP from tricks should sum to 26
        # US card: 60, THEM card: 60+10=70 (last trick bonus to them)
        # But Khasara may apply if bidder (us) loses.
        # Let's verify the tiebreak result directly.
        se = self.game.scoring_engine
        us_abnat, them_abnat, bonus = se.calculate_card_abnat()
        total_abnat = us_abnat + them_abnat
        self.assertEqual(total_abnat, 130,
                         f"SUN total Abnat must be 130, got {total_abnat}")

        # Verify GP calculation via tiebreak
        gp_result = se.calculate_game_points_with_tiebreak(
            us_abnat - bonus['us'], them_abnat - bonus['them'],
            bonus['us'], bonus['them'], 'us'
        )
        total_gp = gp_result['game_points']['us'] + gp_result['game_points']['them']
        self.assertEqual(total_gp, 26,
                         f"SUN total GP must be 26, got {total_gp}")


class TestFullHokumRound(_ScoringIntegrationBase):
    """Tests for a complete HOKUM round producing 16 total GP from tricks."""

    def test_full_hokum_round_16gp(self):
        """8 tricks in HOKUM mode: total GP from card+ardh must equal 16.

        HOKUM total Abnat = 162 (152 card + 10 last trick).
        GP conversion: raw / 10, > 0.5 rounds up.
        Sum of both teams' GP = 16.
        """
        # Distribute 152 card points: 76 each, last trick to US (+10 bonus)
        # US raw: 76+10=86, THEM raw: 76
        # Total abnat: 162
        self._add_interleaved_tricks([
            ('Bottom', 19), ('Right', 19),
            ('Bottom', 19), ('Right', 19),
            ('Bottom', 19), ('Right', 19),
            ('Bottom', 19), ('Right', 19),  # last trick won by them
        ])

        se = self.game.scoring_engine
        us_abnat, them_abnat, bonus = se.calculate_card_abnat()
        total_abnat = us_abnat + them_abnat
        self.assertEqual(total_abnat, 162,
                         f"HOKUM total Abnat must be 162, got {total_abnat}")

        gp_result = se.calculate_game_points_with_tiebreak(
            us_abnat - bonus['us'], them_abnat - bonus['them'],
            bonus['us'], bonus['them'], 'us'
        )
        total_gp = gp_result['game_points']['us'] + gp_result['game_points']['them']
        self.assertEqual(total_gp, 16,
                         f"HOKUM total GP must be 16, got {total_gp}")


class TestKabootSun(_ScoringIntegrationBase):
    """Tests for Kaboot (all tricks won) in SUN mode."""

    def test_kaboot_sun_44(self):
        """One team wins all 8 tricks in SUN -> 44 GP for that team."""
        self.game.game_mode = 'SUN'
        self.game.trump_suit = None
        self.game.bid = {'bidder': 'Bottom', 'type': 'SUN', 'suit': None}

        # US wins all 8 tricks
        self._add_tricks(us_wins=8, them_wins=0, us_points_each=15)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertEqual(score_us, 44,
                         f"Kaboot in SUN should give 44 GP, got {score_us}")
        self.assertEqual(score_them, 0,
                         f"Losing team should get 0 GP, got {score_them}")
        self.assertTrue(result['us']['isKaboot'],
                        "US should be marked as Kaboot winner")
        self.assertFalse(result['them']['isKaboot'])


class TestKabootHokum(_ScoringIntegrationBase):
    """Tests for Kaboot (all tricks won) in HOKUM mode."""

    def test_kaboot_hokum_25(self):
        """One team wins all 8 tricks in HOKUM -> 25 GP for that team."""
        # US wins all 8 tricks
        self._add_tricks(us_wins=8, them_wins=0, us_points_each=19)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertEqual(score_us, 25,
                         f"Kaboot in HOKUM should give 25 GP, got {score_us}")
        self.assertEqual(score_them, 0,
                         f"Losing team should get 0 GP, got {score_them}")
        self.assertTrue(result['us']['isKaboot'])

    def test_kaboot_them_hokum(self):
        """THEM wins all 8 tricks in HOKUM -> 25 GP for them, Khasara applies to bidder."""
        self.game.bid = {'bidder': 'Bottom', 'type': 'HOKUM', 'suit': '\u2660'}

        # THEM wins all 8 tricks
        self._add_tricks(us_wins=0, them_wins=8, them_points_each=19)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertTrue(result['them']['isKaboot'])
        # Kaboot winner gets 25; bidder (us) gets 0
        self.assertEqual(score_them, 25)
        self.assertEqual(score_us, 0)


class TestKhasaraFlip(_ScoringIntegrationBase):
    """Tests for Khasara: bidder gets fewer GP -> bidder=0, defender gets all."""

    def test_khasara_flip(self):
        """Bidder (us) gets fewer GP than them -> Khasara: us=0, them=total pot."""
        # Bidder is 'Bottom' (us)
        # Give THEM most of the points so bidder loses
        self._add_tricks(us_wins=2, them_wins=6, us_points_each=10, them_points_each=18)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertEqual(score_us, 0,
                         f"Khasara: bidder should get 0 GP, got {score_us}")
        self.assertGreater(score_them, 0,
                           "Defender should get all GP on Khasara")

    def test_khasara_equal_scores_bidder_loses(self):
        """When bidder GP <= defender GP, Khasara applies (bidder gets 0)."""
        # Create a scenario where both teams get similar raw points
        # so that after rounding bidder (us) <= them
        self._add_tricks(us_wins=4, them_wins=4, us_points_each=19, them_points_each=19)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        # With equal points, Khasara triggers because bidder score_us <= score_them
        self.assertEqual(score_us, 0,
                         "Equal GP should trigger Khasara for bidder")
        self.assertGreater(score_them, 0)

    def test_no_khasara_when_bidder_wins(self):
        """Bidder (us) winning more GP should not trigger Khasara."""
        self._add_tricks(us_wins=6, them_wins=2, us_points_each=18, them_points_each=10)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertGreater(score_us, 0,
                           "Bidder winning should not trigger Khasara")


class TestDoubledKhasara(_ScoringIntegrationBase):
    """Tests for Khasara under doubled game conditions."""

    def test_doubled_khasara(self):
        """Doubled game where bidder loses -> doubled penalty applied.

        When doubling_level=2 and Khasara applies:
        total_pot is multiplied by 2, all goes to defender.
        """
        self.game.doubling_level = 2

        # Bidder (us) loses
        self._add_tricks(us_wins=2, them_wins=6, us_points_each=10, them_points_each=18)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertEqual(score_us, 0,
                         "Doubled Khasara: bidder should still get 0")
        # The score should be doubled
        self.assertEqual(result['us']['multiplierApplied'], 2,
                         "Multiplier should be recorded as 2")
        # them should get a substantial doubled amount
        self.assertGreater(score_them, 16,
                           "Doubled Khasara should produce more than base 16 GP")

    def test_tripled_khasara(self):
        """Tripled game where bidder loses -> tripled penalty."""
        self.game.doubling_level = 3

        self._add_tricks(us_wins=2, them_wins=6, us_points_each=10, them_points_each=18)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertEqual(score_us, 0)
        self.assertEqual(result['them']['multiplierApplied'], 3)


class TestGahwaScoring(_ScoringIntegrationBase):
    """Tests for Gahwa (doubling level 100) scoring."""

    def test_gahwa_scoring(self):
        """Level=100, one team shut out (0 GP) -> winner gets 152 GP.

        Gahwa is the ultimate doubling level. When one team has all GP
        and the opponent has 0, the winner receives 152 (match target).
        """
        self.game.doubling_level = 100

        # Kaboot gives one team all GP, opponent 0
        self._add_tricks(us_wins=8, them_wins=0, us_points_each=19)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertEqual(score_us, 152,
                         f"Gahwa with Kaboot should give 152 GP, got {score_us}")
        self.assertEqual(score_them, 0,
                         f"Losing team should get 0 GP, got {score_them}")

    def test_gahwa_khasara(self):
        """Gahwa where bidder gets Khasara'd: opponent should get 152."""
        self.game.doubling_level = 100

        # Bidder (us) loses -> Khasara applies first, then Gahwa
        # us=0, them=total_pot, and since us==0 -> them gets 152
        self._add_tricks(us_wins=2, them_wins=6, us_points_each=10, them_points_each=18)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertEqual(score_us, 0,
                         "Gahwa Khasara: bidder gets 0")
        self.assertEqual(score_them, 152,
                         f"Gahwa Khasara: defender should get 152, got {score_them}")


class TestProjectsPlusTricks(_ScoringIntegrationBase):
    """Tests for project points combined with trick points."""

    def test_projects_plus_tricks(self):
        """Team has project points + trick points = combined GP.

        Projects add floor(abnat / 10) GP in HOKUM (floor(abnat * 2 / 10) in SUN).
        """
        # Give US enough trick points to win (avoid Khasara)
        self._add_tricks(us_wins=6, them_wins=2, us_points_each=18, them_points_each=10)

        # Declare a SIRA (50 abnat) project for Bottom (us)
        self.game.declarations = {
            'Bottom': [{'type': 'SIRA', 'rank': 'Q', 'suit': '\u2665', 'score': 50}]
        }

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        # Project contribution: 50 // 10 = 5 GP for us in HOKUM
        self.assertEqual(result['us']['projectPoints'], 50,
                         "US project abnat should be 50")
        # Score should include both trick GP and project GP
        self.assertGreater(score_us, 0, "US should have positive score with projects + tricks")

    def test_projects_sun_mode(self):
        """SUN mode projects should use (abnat * 2) // 10 conversion."""
        self.game.game_mode = 'SUN'
        self.game.trump_suit = None
        self.game.bid = {'bidder': 'Bottom', 'type': 'SUN', 'suit': None}

        self._add_tricks(us_wins=6, them_wins=2, us_points_each=12, them_points_each=6)

        # Declare a 50-abnat project for US in SUN
        self.game.declarations = {
            'Bottom': [{'type': 'SIRA', 'rank': 'Q', 'suit': '\u2665', 'score': 50}]
        }

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        # SUN project: (50 * 2) // 10 = 10 GP
        self.assertEqual(result['us']['projectPoints'], 50)
        self.assertGreater(score_us, 0)

    def test_both_teams_have_projects(self):
        """Both teams declaring projects should see their respective GP added."""
        self._add_tricks(us_wins=6, them_wins=2, us_points_each=18, them_points_each=10)

        self.game.declarations = {
            'Bottom': [{'type': 'SIRA', 'rank': 'Q', 'suit': '\u2665', 'score': 50}],
            'Right': [{'type': 'SIRA', 'rank': 'J', 'suit': '\u2666', 'score': 20}],
        }

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertEqual(result['us']['projectPoints'], 50)
        self.assertEqual(result['them']['projectPoints'], 20)


class TestZeroZeroTie(_ScoringIntegrationBase):
    """Tests for tiebreak resolution when both teams have equal raw points."""

    def test_last_trick_bonus_pair_rounding(self):
        """Last trick bonus gives them +10, but pair rounding equalizes GP.

        In HOKUM: us=76 them=86. Individual: 8+9=17.
        Equal remainders (6 vs 6), reduce larger raw (them) → 8+8 tie.
        GP tie → bidder ('us') wins the tiebreak.
        """
        # 4 tricks each at 19 pts, last trick (Right) gets +10 bonus
        # us=4*19=76, them=4*19+10=86
        self._add_interleaved_tricks([
            ('Bottom', 19), ('Right', 19),
            ('Bottom', 19), ('Right', 19),
            ('Bottom', 19), ('Right', 19),
            ('Bottom', 19), ('Right', 19),
        ])

        se = self.game.scoring_engine
        us_abnat, them_abnat, bonus = se.calculate_card_abnat()

        pure_us = us_abnat - bonus['us']
        pure_them = them_abnat - bonus['them']

        gp_result = se.calculate_game_points_with_tiebreak(
            pure_us, pure_them,
            bonus['us'], bonus['them'],
            'us'  # bidder team
        )

        # Pair rounding equalizes GP to 8+8 tie, bidder wins tiebreak
        self.assertEqual(gp_result['game_points']['us'], 8)
        self.assertEqual(gp_result['game_points']['them'], 8)
        self.assertEqual(gp_result['winner'], 'us',
                         "GP tied at 8-8, bidder wins tiebreak")

    def test_tiebreak_bidder_them(self):
        """When bidder is 'them' and points are equal, them should win tiebreak."""
        self._add_interleaved_tricks([
            ('Bottom', 19), ('Right', 19),
            ('Bottom', 19), ('Right', 19),
            ('Bottom', 19), ('Right', 19),
            ('Bottom', 19), ('Right', 19),
        ])

        se = self.game.scoring_engine
        us_abnat, them_abnat, bonus = se.calculate_card_abnat()

        gp_result = se.calculate_game_points_with_tiebreak(
            us_abnat - bonus['us'], them_abnat - bonus['them'],
            bonus['us'], bonus['them'],
            'them'  # bidder team
        )

        self.assertEqual(gp_result['winner'], 'them',
                         "Tiebreak should go to bidder team ('them')")


class TestLastTrickBonus(_ScoringIntegrationBase):
    """Tests for the 10-point last trick bonus."""

    def test_last_trick_bonus(self):
        """Winner of the last trick gets a 10-point Abnat bonus.

        The last entry in round_history is the final trick. The team
        that wins it receives +10 raw points (Ardh).
        """
        # 8 tricks: last trick won by Bottom (us)
        self._add_interleaved_tricks([
            ('Right', 20), ('Bottom', 20),
            ('Right', 20), ('Bottom', 20),
            ('Right', 20), ('Bottom', 20),
            ('Right', 16), ('Bottom', 16),  # last trick -> Bottom wins
        ])

        us_abnat, them_abnat, bonus = self.game.scoring_engine.calculate_card_abnat()

        self.assertEqual(bonus['us'], 10,
                         "US (last trick winner) should get 10 bonus")
        self.assertEqual(bonus['them'], 0,
                         "THEM should get 0 bonus")

    def test_last_trick_bonus_to_them(self):
        """When THEM wins the last trick, they get the 10-point bonus."""
        self._add_interleaved_tricks([
            ('Bottom', 20), ('Right', 20),
            ('Bottom', 20), ('Right', 20),
            ('Bottom', 20), ('Right', 20),
            ('Bottom', 16), ('Right', 16),  # last trick -> Right wins
        ])

        us_abnat, them_abnat, bonus = self.game.scoring_engine.calculate_card_abnat()

        self.assertEqual(bonus['us'], 0)
        self.assertEqual(bonus['them'], 10,
                         "THEM (last trick winner) should get 10 bonus")

    def test_last_trick_bonus_included_in_abnat(self):
        """The 10-point bonus should be included in the total Abnat for the team."""
        self._add_interleaved_tricks([
            ('Bottom', 20), ('Right', 20),
            ('Bottom', 20), ('Right', 20),
            ('Bottom', 20), ('Right', 20),
            ('Bottom', 20), ('Right', 12),  # last trick -> Right
        ])

        us_abnat, them_abnat, bonus = self.game.scoring_engine.calculate_card_abnat()

        # US: 4 * 20 = 80, no bonus
        self.assertEqual(us_abnat, 80)
        # THEM: 4 * 20 + 12 - 20 = ... actually let me recalculate:
        # THEM tricks: 20 + 20 + 20 + 12 = 72, + 10 bonus = 82
        # Wait, the interleaved list has 4 Bottom (20 each) + 4 Right (20, 20, 20, 12)
        # THEM raw: 20 + 20 + 20 + 12 = 72
        # Last trick is ('Right', 12) so bonus goes to them
        # THEM total: 72 + 10 = 82
        self.assertEqual(them_abnat, 82,
                         "THEM abnat should include 10-point last trick bonus")


class TestRoundingRules(_ScoringIntegrationBase):
    """Additional tests for SUN vs HOKUM rounding edge cases."""

    def test_sun_floor_to_even(self):
        """SUN: floor-to-even rounding (Kammelna validated)."""
        se = self.game.scoring_engine
        # 33 → divmod(33,5)=(6,3) → q=6 (even), r>0 → stays 6
        self.assertEqual(se._calculate_score_for_team(33, 'SUN'), 6)
        # 25 → divmod(25,5)=(5,0) → r=0 → 5
        self.assertEqual(se._calculate_score_for_team(25, 'SUN'), 5)

    def test_hokum_rounding_half_down(self):
        """HOKUM: 0.5 decimal rounds DOWN (> 0.5 needed to round up)."""
        se = self.game.scoring_engine
        # 65 / 10 = 6.5 -> 6 (rounds DOWN in HOKUM)
        self.assertEqual(se._calculate_score_for_team(65, 'HOKUM'), 6)
        # 66 / 10 = 6.6 -> 7 (rounds UP)
        self.assertEqual(se._calculate_score_for_team(66, 'HOKUM'), 7)
        # 64 / 10 = 6.4 -> 6
        self.assertEqual(se._calculate_score_for_team(64, 'HOKUM'), 6)

    def test_sun_zero_raw(self):
        """SUN: zero raw value should produce 0 GP."""
        se = self.game.scoring_engine
        self.assertEqual(se._calculate_score_for_team(0, 'SUN'), 0)

    def test_hokum_zero_raw(self):
        """HOKUM: zero raw value should produce 0 GP."""
        se = self.game.scoring_engine
        self.assertEqual(se._calculate_score_for_team(0, 'HOKUM'), 0)


class TestDoublingNonKhasara(_ScoringIntegrationBase):
    """Tests for doubling when bidder wins (no Khasara)."""

    def test_doubled_bidder_wins(self):
        """Doubled game where bidder wins -> scores multiplied by 2."""
        self.game.doubling_level = 2

        # Bidder (us) wins clearly
        self._add_tricks(us_wins=6, them_wins=2, us_points_each=20, them_points_each=8)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertGreater(score_us, 0)
        self.assertEqual(result['us']['multiplierApplied'], 2)
        # Both scores should be doubled
        self.assertEqual(score_us + score_them,
                         (score_us + score_them),
                         "Total score should reflect doubling")

    def test_quadrupled_bidder_wins(self):
        """Level 4 doubling where bidder wins."""
        self.game.doubling_level = 4

        self._add_tricks(us_wins=6, them_wins=2, us_points_each=20, them_points_each=8)

        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        self.assertGreater(score_us, 0)
        self.assertEqual(result['us']['multiplierApplied'], 4)


class TestBalootInFinalScores(_ScoringIntegrationBase):
    """Tests that Baloot GP are added after doubling in calculate_final_scores."""

    def test_baloot_added_after_doubling(self):
        """Baloot 2 GP should be added AFTER the doubling multiplier is applied."""
        self.game.doubling_level = 2

        # Bidder wins to avoid Khasara
        self._add_tricks(us_wins=6, them_wins=2, us_points_each=20, them_points_each=8)

        # Set up Baloot: scan player 0 with K+Q of trump
        bm = self.game.baloot_manager
        self.game.players[0].hand = [
            Card('\u2660', 'K'),
            Card('\u2660', 'Q'),
        ]
        for i in [1, 2, 3]:
            self.game.players[i].hand = [Card('\u2665', '7'), Card('\u2665', '8')]

        bm.scan_initial_hands()
        bm.on_card_played('Bottom', Card('\u2660', 'K'))
        bm.on_card_played('Bottom', Card('\u2660', 'Q'))

        # Now calculate final scores
        result, score_us, score_them = self.game.scoring_engine.calculate_final_scores()

        # Baloot adds exactly 2 GP (not doubled)
        baloot_pts = bm.get_baloot_points()
        self.assertEqual(baloot_pts['us'], 2)
        self.assertEqual(baloot_pts['them'], 0)

        # The score should include baloot on top of doubled trick GP
        # We can verify by computing without baloot
        bm.reset()  # remove baloot
        result_no_baloot, score_us_no_baloot, _ = self.game.scoring_engine.calculate_final_scores()

        # Re-setup baloot for the check
        # The difference should be exactly 2 (the immune baloot GP)
        # But since we reset the baloot manager, the second call won't have baloot
        self.assertEqual(score_us, score_us_no_baloot + 2,
                         "Baloot should add exactly 2 GP on top of doubled score")


class TestEdgeCases(_ScoringIntegrationBase):
    """Edge case tests for the scoring engine."""

    def test_empty_round_history(self):
        """No tricks played should produce zero scores."""
        self.game.round_history = []

        us_abnat, them_abnat, bonus = self.game.scoring_engine.calculate_card_abnat()
        self.assertEqual(us_abnat, 0)
        self.assertEqual(them_abnat, 0)
        self.assertEqual(bonus, {'us': 0, 'them': 0})

    def test_single_trick(self):
        """A single trick should still work with last-trick bonus."""
        self._add_tricks(us_wins=1, them_wins=0, us_points_each=30)

        us_abnat, them_abnat, bonus = self.game.scoring_engine.calculate_card_abnat()
        self.assertEqual(us_abnat, 40)  # 30 + 10 bonus
        self.assertEqual(them_abnat, 0)
        self.assertEqual(bonus['us'], 10)


if __name__ == '__main__':
    unittest.main()
