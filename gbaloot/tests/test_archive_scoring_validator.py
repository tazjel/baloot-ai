"""Tests for archive_scoring_validator — GP conversion, khasara, kaboot, radda."""
from __future__ import annotations

import pytest
from pathlib import Path

from gbaloot.tools.archive_scoring_validator import (
    card_gp_sun,
    card_gp_hokum,
    project_gp_sun,
    project_gp_hokum,
    validate_round,
    validate_all,
    ValidationReport,
    DECK_TOTAL_SUN,
    DECK_TOTAL_HOKUM,
    GP_TARGET_SUN,
    GP_TARGET_HOKUM,
    KABOOT_GP_SUN,
    KABOOT_GP_HOKUM,
    BALOOT_GP,
    GAHWA_FLAT,
)


# ── GP Conversion Functions ──────────────────────────────────────────


class TestCardGpSun:
    """SUN card GP: floor(card_abnat / 5)."""

    def test_exact_multiple(self):
        assert card_gp_sun(50) == 10
        assert card_gp_sun(0) == 0
        assert card_gp_sun(130) == 26

    def test_truncation(self):
        """Floor division truncates toward zero."""
        assert card_gp_sun(51) == 10
        assert card_gp_sun(54) == 10
        assert card_gp_sun(59) == 11

    def test_common_values(self):
        """Common card abnat values in SUN."""
        assert card_gp_sun(60) == 12  # Half of 120
        assert card_gp_sun(120) == 24
        assert card_gp_sun(130) == 26  # 120 + 10 last trick

    def test_boundary_values(self):
        assert card_gp_sun(1) == 0
        assert card_gp_sun(4) == 0
        assert card_gp_sun(5) == 1
        assert card_gp_sun(9) == 1
        assert card_gp_sun(10) == 2


class TestCardGpHokum:
    """HOKUM card GP: floor(card_abnat / 10), >0.5 rounds up."""

    def test_exact_multiple(self):
        assert card_gp_hokum(100) == 10
        assert card_gp_hokum(0) == 0
        assert card_gp_hokum(160) == 16

    def test_asymmetric_rounding(self):
        """0.5 exactly rounds DOWN, >0.5 rounds UP."""
        assert card_gp_hokum(15) == 1   # 1.5 → 1 (rounds down at 0.5)
        assert card_gp_hokum(16) == 2   # 1.6 → 2 (rounds up at >0.5)
        assert card_gp_hokum(25) == 2   # 2.5 → 2
        assert card_gp_hokum(26) == 3   # 2.6 → 3

    def test_common_values(self):
        assert card_gp_hokum(76) == 8   # 7.6 → 8
        assert card_gp_hokum(152) == 15  # 15.2 → 15
        assert card_gp_hokum(162) == 16  # 16.2 → 16


class TestProjectGpSun:
    """SUN project GP: floor(project_abnat * 2 / 10)."""

    def test_sira_20(self):
        """sira declaration = 20 abnat → 4 GP."""
        assert project_gp_sun(20) == 4

    def test_50_declaration(self):
        """50 declaration → 10 GP."""
        assert project_gp_sun(50) == 10

    def test_100_declaration(self):
        """100 declaration → 20 GP."""
        assert project_gp_sun(100) == 20

    def test_zero(self):
        assert project_gp_sun(0) == 0


class TestProjectGpHokum:
    """HOKUM project GP: floor(project_abnat / 10)."""

    def test_sira_20(self):
        """sira declaration = 20 abnat → 2 GP."""
        assert project_gp_hokum(20) == 2

    def test_50_declaration(self):
        assert project_gp_hokum(50) == 5

    def test_zero(self):
        assert project_gp_hokum(0) == 0


# ── Round Validation ─────────────────────────────────────────────────


class TestValidateRound:
    """Test validate_round with synthetic result dicts."""

    def test_waraq_returns_none(self):
        """Waraq (no result) returns None."""
        assert validate_round(None, "test.json", 0) is None

    def test_no_mode_returns_none(self):
        assert validate_round({"m": 0}, "test.json", 0) is None

    def test_basic_sun_round(self):
        """Simple SUN round with known values."""
        result = {
            "m": 1, "b": 1, "w": 1, "lmw": 1, "em": 1,
            "e1": 80, "e2": 40, "p1": 90, "p2": 40,
            "r1": [], "r2": [],
            "s1": 18, "s2": 8,
        }
        rv = validate_round(result, "test.json", 0)
        assert rv is not None
        assert rv.game_mode == "SUN"
        assert rv.e_sum == 120
        assert rv.e_sum_ok is True

    def test_basic_hokum_round(self):
        """Simple HOKUM round with known values."""
        result = {
            "m": 2, "b": 1, "w": 1, "lmw": 1, "em": 1,
            "e1": 100, "e2": 52, "p1": 110, "p2": 52,
            "r1": [], "r2": [],
            "s1": 11, "s2": 5,
        }
        rv = validate_round(result, "test.json", 0)
        assert rv is not None
        assert rv.game_mode == "HOKUM"
        assert rv.e_sum == 152
        assert rv.e_sum_ok is True

    def test_kaboot_sun(self):
        """Kaboot in SUN mode — base 44 GP + projects."""
        result = {
            "m": 1, "b": 1, "w": 1, "lmw": 1, "em": 1, "kbt": 1,
            "e1": 120, "e2": 0, "p1": 140, "p2": 0,
            "r1": [{"n": "sira", "val": "20"}], "r2": [],
            "s1": 48, "s2": 0,
        }
        rv = validate_round(result, "test.json", 0)
        assert rv is not None
        assert rv.is_kaboot_archive is True
        # base 44 + project_gp_sun(20) = 44 + 4 = 48
        assert rv.s1_computed == 48
        assert rv.gp_ok is True

    def test_kaboot_hokum_with_baloot(self):
        """Kaboot in HOKUM with baloot declaration."""
        result = {
            "m": 2, "b": 2, "w": 2, "lmw": 2, "em": 1, "kbt": 1,
            "e1": 0, "e2": 152, "p1": 0, "p2": 152,
            "r1": [], "r2": [{"n": "baloot", "val": "0"}],
            "s1": 0, "s2": 27,
        }
        rv = validate_round(result, "test.json", 0)
        assert rv is not None
        # base 25 + baloot 2 = 27
        assert rv.s2_computed == 27
        assert rv.gp_ok is True

    def test_khasara_bidder_loses(self):
        """Khasara: bidder GP <= opponent → all to opponent."""
        # SUN, bidder=team1, e1=40 e2=80, lmw=2
        # ca1=40, ca2=90 → cg1=8, cg2=18 (total=26, no tiebreak)
        # g1=8, g2=18. Bidder (team1) has 8 < 18 → khasara
        # pot = 26, team1=0, team2=26
        result = {
            "m": 1, "b": 1, "w": 2, "lmw": 2, "em": 1,
            "e1": 40, "e2": 80, "p1": 40, "p2": 90,
            "r1": [], "r2": [],
            "s1": 0, "s2": 26,
        }
        rv = validate_round(result, "test.json", 0)
        assert rv is not None
        assert rv.is_khasara is True
        assert rv.s1_computed == 0
        assert rv.s2_computed == 26
        assert rv.gp_ok is True

    def test_radda_doubling(self):
        """Radda (rd=True) doubles GP — winner takes all × 2."""
        # HOKUM, b=1, w=1, e1=100 e2=52, lmw=1
        # ca1=110, ca2=52 → cg1=11, cg2=5 (total=16, exact)
        # g1=11, g2=5. No khasara (bidder has 11 > 5).
        # Radda: total=16, winner(team1) gets 16*2=32, loser=0
        result = {
            "m": 2, "b": 1, "w": 1, "lmw": 1, "em": 1,
            "e1": 100, "e2": 52, "p1": 110, "p2": 52,
            "r1": [], "r2": [],
            "s1": 32, "s2": 0,
        }
        rv = validate_round(result, "test.json", 0, has_rd=True)
        assert rv is not None
        assert rv.is_rd is True
        assert rv.s1_computed == 32
        assert rv.s2_computed == 0
        assert rv.gp_ok is True

    def test_gahwa_flat_152(self):
        """Gahwa (em >= 4) gives flat 152 to winner."""
        result = {
            "m": 2, "b": 1, "w": 1, "lmw": 1, "em": 4,
            "e1": 100, "e2": 52, "p1": 110, "p2": 52,
            "r1": [], "r2": [],
            "s1": 152, "s2": 0,
        }
        rv = validate_round(result, "test.json", 0)
        assert rv is not None
        assert rv.s1_computed == 152
        assert rv.s2_computed == 0
        assert rv.gp_ok is True

    def test_baloot_immune_to_doubling(self):
        """Baloot GP is added AFTER em multiplier."""
        # HOKUM, b=1, w=1, em=2
        # ca1=110, ca2=52 → cg1=11, cg2=5
        # g1=11, g2=5. No khasara. em=2: g1=22, g2=10.
        # Baloot for team1: +2. g1=24, g2=10.
        result = {
            "m": 2, "b": 1, "w": 1, "lmw": 1, "em": 2,
            "e1": 100, "e2": 52, "p1": 110, "p2": 52,
            "r1": [{"n": "baloot", "val": "0"}], "r2": [],
            "s1": 24, "s2": 10,
        }
        rv = validate_round(result, "test.json", 0)
        assert rv is not None
        assert rv.s1_computed == 24
        assert rv.s2_computed == 10
        assert rv.gp_ok is True

    def test_declarations_string_values(self):
        """Declaration values are stored as strings in archive format."""
        result = {
            "m": 1, "b": 1, "w": 1, "lmw": 1, "em": 1,
            "e1": 80, "e2": 40, "p1": 100, "p2": 40,
            "r1": [{"n": "sira", "val": "20"}], "r2": [],
            "s1": 22, "s2": 8,
        }
        rv = validate_round(result, "test.json", 0)
        assert rv is not None
        # ca1=90, ca2=40 → cg1=18, cg2=8 (total=26)
        # pg1=project_gp_sun(20)=4, g1=18+4=22, g2=8
        assert rv.s1_computed == 22
        assert rv.s2_computed == 8
        assert rv.gp_ok is True

    def test_ashkal_is_sun(self):
        """Ashkal mode (m=3) is treated as SUN."""
        result = {
            "m": 3, "b": 1, "w": 1, "lmw": 1, "em": 1,
            "e1": 60, "e2": 60, "p1": 70, "p2": 60,
            "r1": [], "r2": [],
        }
        rv = validate_round(result, "test.json", 0)
        assert rv is not None
        assert rv.game_mode == "SUN"


# ── Full Pipeline Integration ────────────────────────────────────────


class TestValidateAll:
    """Integration tests running against real archive data."""

    @pytest.fixture(scope="class")
    def report(self):
        """Run validation once against all archives."""
        archive_dir = Path(
            "gbaloot/data/archive_captures/mobile_export/savedGames"
        )
        if not archive_dir.exists():
            pytest.skip("Archive data not available")
        return validate_all(archive_dir)

    def test_total_games(self, report: ValidationReport):
        assert report.total_games == 109

    def test_validated_rounds(self, report: ValidationReport):
        assert report.validated_rounds == 1095

    def test_waraq_rounds(self, report: ValidationReport):
        assert report.waraq_rounds == 534

    def test_kaboot_rounds(self, report: ValidationReport):
        assert report.kaboot_rounds == 125

    def test_kaboot_gp_100_percent(self, report: ValidationReport):
        """Kaboot GP must be 100% agreement."""
        assert report.kaboot_matches == report.kaboot_rounds

    def test_card_abnat_above_98(self, report: ValidationReport):
        """Card abnat should be > 98% agreement."""
        pct = 100 * report.e_sum_matches / report.validated_rounds
        assert pct > 98.0

    def test_p_formula_above_88(self, report: ValidationReport):
        """P formula should be > 88% agreement (kaboot rounds are tricky)."""
        pct = 100 * report.p_matches / report.validated_rounds
        assert pct > 88.0

    def test_gp_conversion_above_87(self, report: ValidationReport):
        """GP conversion should be > 87% agreement."""
        pct = 100 * report.gp_matches / report.validated_rounds
        assert pct > 87.0

    def test_non_kaboot_gp_above_85(self, report: ValidationReport):
        """Non-kaboot GP should be > 85% agreement."""
        non_kbt = report.validated_rounds - report.kaboot_rounds
        non_kbt_gp = report.gp_matches - report.kaboot_matches
        pct = 100 * non_kbt_gp / non_kbt
        assert pct > 85.0

    def test_cumulative_above_99(self, report: ValidationReport):
        """Cumulative scores should be > 99% agreement."""
        pct = 100 * report.cumulative_matches / report.total_games
        assert pct > 99.0

    def test_known_mismatch_categories(self, report: ValidationReport):
        """All mismatch categories are known/expected."""
        known_cats = {
            "off_by_1", "off_by_2", "false_khasara",
            "non_bidder_khasara", "doubled", "qayd",
            "tie_mismatch", "kaboot", "other",
        }
        for cat in report.gp_mismatch_categories:
            assert cat in known_cats, f"Unknown mismatch category: {cat}"

    def test_off_by_1_are_sun_only(self, report: ValidationReport):
        """off_by_1 mismatches should only occur in SUN mode."""
        for gv in report.games:
            for rv in gv.rounds:
                if rv.gp_mismatch_category == "off_by_1":
                    assert rv.game_mode == "SUN", (
                        f"off_by_1 in HOKUM: {rv.file_name} R{rv.round_index}"
                    )


# ── Constant Validation ──────────────────────────────────────────────


class TestConstants:
    """Verify game constants match expected values."""

    def test_sun_deck_total(self):
        assert DECK_TOTAL_SUN == 120

    def test_hokum_deck_total(self):
        assert DECK_TOTAL_HOKUM == 152

    def test_sun_gp_target(self):
        assert GP_TARGET_SUN == 26

    def test_hokum_gp_target(self):
        assert GP_TARGET_HOKUM == 16

    def test_kaboot_sun(self):
        assert KABOOT_GP_SUN == 44

    def test_kaboot_hokum(self):
        assert KABOOT_GP_HOKUM == 25

    def test_baloot_gp(self):
        assert BALOOT_GP == 2

    def test_gahwa_flat(self):
        assert GAHWA_FLAT == 152
