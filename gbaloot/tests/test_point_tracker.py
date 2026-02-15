"""
Tests for point tracker (gbaloot.core.point_tracker).

Covers: rounding formulas (SUN/HOKUM), single-round analysis, 8-trick
round consistency, last trick bonus, incomplete rounds, analyze_session_points.
"""
import pytest

from game_engine.models.card import Card
from gbaloot.core.point_tracker import (
    round_sun,
    round_hokum,
    get_card_points,
    analyze_round_points,
    analyze_session_points,
    PointAnalysis,
    EXPECTED_CARD_ABNAT_SUN,
    EXPECTED_CARD_ABNAT_HOKUM,
    LAST_TRICK_BONUS,
    TARGET_GP_SUN,
    TARGET_GP_HOKUM,
)
from gbaloot.core.trick_extractor import (
    ExtractedTrick,
    ExtractedRound,
    ExtractionResult,
)


# ── Helpers ─────────────────────────────────────────────────────────

def _make_trick(
    trick_number: int,
    round_index: int = 0,
    cards_by_seat: dict | None = None,
    winner_seat: int = 0,
    lead_suit_idx: int = 0,
    game_mode_raw: str = "ashkal",
    trump_suit_idx: int | None = None,
) -> ExtractedTrick:
    """Build an ExtractedTrick for testing."""
    if cards_by_seat is None:
        # Default: ♠7(5), ♠8(6), ♠9(7), ♠10(8) — 10 points total
        cards_by_seat = {0: 5, 1: 6, 2: 7, 3: 8}
    return ExtractedTrick(
        trick_number=trick_number,
        round_index=round_index,
        cards_by_seat=cards_by_seat,
        winner_seat=winner_seat,
        lead_suit_idx=lead_suit_idx,
        game_mode_raw=game_mode_raw,
        trump_suit_idx=trump_suit_idx,
        scores_snapshot=[6, 6, 6, 6],
        timestamp=1000.0 + trick_number * 100,
    )


def _make_round(
    tricks: list[ExtractedTrick],
    round_index: int = 0,
    mode: str = "ashkal",
    trump: int | None = None,
) -> ExtractedRound:
    """Build an ExtractedRound for testing."""
    return ExtractedRound(
        round_index=round_index,
        game_mode_raw=mode,
        trump_suit_idx=trump,
        dealer_seat=0,
        tricks=tricks,
    )


# ── Rounding Formulas ────────────────────────────────────────────────

class TestRoundSun:
    """SUN rounding: raw * 2 / 10, rounds up at >= 0.5."""

    def test_exact_65(self):
        """65 * 2 / 10 = 13.0 → 13."""
        assert round_sun(65) == 13

    def test_rounds_up_at_half(self):
        """75 * 2 / 10 = 15.0 → 15. 73 * 2 / 10 = 14.6 → 15."""
        assert round_sun(75) == 15
        assert round_sun(73) == 15

    def test_rounds_down_below_half(self):
        """71 * 2 / 10 = 14.2 → 14."""
        assert round_sun(71) == 14

    def test_full_round_130(self):
        """Full round 130 Abnat → 26 GP."""
        assert round_sun(130) == 26

    def test_zero(self):
        assert round_sun(0) == 0

    def test_team_split_sums_to_26(self):
        """Two complementary teams should sum to 26 GP (130 total)."""
        # Team A gets 70, Team B gets 60
        assert round_sun(70) + round_sun(60) == 26


class TestRoundHokum:
    """HOKUM rounding: raw / 10, rounds up only at > 0.5 (strict)."""

    def test_exact_85(self):
        """85 / 10 = 8.5 → rounds DOWN to 8 (strict > 0.5)."""
        assert round_hokum(85) == 8

    def test_rounds_up_above_half(self):
        """86 / 10 = 8.6 → rounds UP to 9."""
        assert round_hokum(86) == 9

    def test_rounds_down_at_half(self):
        """85 / 10 = 8.5 → rounds DOWN (strict: needs > 0.5)."""
        assert round_hokum(85) == 8

    def test_full_round_162(self):
        """Full round 162 Abnat → 16 GP."""
        assert round_hokum(162) == 16

    def test_zero(self):
        assert round_hokum(0) == 0


# ── get_card_points ──────────────────────────────────────────────────

class TestGetCardPoints:

    def test_sun_ace(self):
        assert get_card_points(Card("♠", "A"), "SUN", None) == 11

    def test_hokum_trump_jack(self):
        assert get_card_points(Card("♥", "J"), "HOKUM", "♥") == 20

    def test_hokum_non_trump_jack(self):
        assert get_card_points(Card("♠", "J"), "HOKUM", "♥") == 2  # SUN value

    def test_no_points_seven(self):
        assert get_card_points(Card("♦", "7"), "SUN", None) == 0


# ── analyze_round_points ────────────────────────────────────────────

class TestAnalyzeRoundPoints:

    def test_single_trick_analysis(self):
        """Single trick → incomplete round, no last trick bonus."""
        trick = _make_trick(1, cards_by_seat={0: 5, 1: 6, 2: 7, 3: 8}, winner_seat=0)
        # ♠7(0)+♠8(0)+♠9(0)+♠10(10) = 10 pts, won by seat 0 (team_02)
        rnd = _make_round([trick])
        analysis = analyze_round_points(rnd, "SUN", None)
        assert analysis.raw_abnat_team_02 == 10
        assert analysis.raw_abnat_team_13 == 0
        assert analysis.is_complete_round is False
        assert analysis.last_trick_team == ""  # No last trick for incomplete

    def test_points_assigned_to_winner(self):
        """All trick points go to the winning team, not the playing seats."""
        # Seat 1 (team_13) wins. Cards played by seats 0,1,2,3
        trick = _make_trick(1, cards_by_seat={0: 12, 1: 8, 2: 11, 3: 5}, winner_seat=1)
        # ♠A(11)+♠10(10)+♠K(4)+♠7(0) = 25 pts → all to team_13
        rnd = _make_round([trick])
        analysis = analyze_round_points(rnd, "SUN", None)
        assert analysis.raw_abnat_team_02 == 0  # team_02 gets nothing
        assert analysis.raw_abnat_team_13 == 25  # winner gets all

    def test_eight_trick_sun_round_consistency(self):
        """A complete 8-trick SUN round should have 120 card points."""
        # Build 8 tricks that together sum to 120 SUN card points
        # Each of 4 suits has: A(11)+10(10)+K(4)+Q(3)+J(2)+9(0)+8(0)+7(0) = 30
        # 4 suits × 30 = 120
        # For simplicity, make 8 tricks with known point totals

        # Trick 1: all ♠ high cards → 11+10+4+3 = 28 pts, seat 0 wins
        t1 = _make_trick(1, cards_by_seat={0: 12, 1: 8, 2: 11, 3: 10}, winner_seat=0)
        # ♠A(11) + ♠10(10) + ♠K(4) + ♠Q(3) = 28

        # Trick 2: ♠ low cards → 2+0+0+0 = 2, seat 1 wins
        t2 = _make_trick(2, cards_by_seat={0: 9, 1: 7, 2: 6, 3: 5}, winner_seat=1)
        # ♠J(2) + ♠9(0) + ♠8(0) + ♠7(0) = 2

        # Trick 3: all ♥ high → 11+10+4+3 = 28, seat 2 wins
        t3 = _make_trick(3, cards_by_seat={0: 25, 1: 21, 2: 24, 3: 23}, winner_seat=2)
        # ♥A(11) + ♥10(10) + ♥K(4) + ♥Q(3) = 28

        # Trick 4: ♥ low → 2+0+0+0 = 2, seat 3 wins
        t4 = _make_trick(4, cards_by_seat={0: 22, 1: 20, 2: 19, 3: 18}, winner_seat=3)
        # ♥J(2) + ♥9(0) + ♥8(0) + ♥7(0) = 2

        # Trick 5: all ♣ high → 28, seat 0 wins
        t5 = _make_trick(5, cards_by_seat={0: 38, 1: 34, 2: 37, 3: 36}, winner_seat=0)
        # ♣A(11) + ♣10(10) + ♣K(4) + ♣Q(3) = 28 (wrong - need correct indices)
        # ♣ suit idx=2, A=2*13+12=38, 10=2*13+8=34, K=2*13+11=37, Q=2*13+10=36

        # Trick 6: ♣ low → 2+0+0+0 = 2, seat 1 wins
        t6 = _make_trick(6, cards_by_seat={0: 35, 1: 33, 2: 32, 3: 31}, winner_seat=1)
        # ♣J(2) + ♣9(0) + ♣8(0) + ♣7(0) = 2

        # Trick 7: all ♦ high → 28, seat 0 wins
        t7 = _make_trick(7, cards_by_seat={0: 51, 1: 47, 2: 50, 3: 49}, winner_seat=0)
        # ♦A(11) + ♦10(10) + ♦K(4) + ♦Q(3) = 28

        # Trick 8: ♦ low → 2+0+0+0 = 2, seat 0 wins
        t8 = _make_trick(8, cards_by_seat={0: 48, 1: 46, 2: 45, 3: 44}, winner_seat=0)
        # ♦J(2) + ♦9(0) + ♦8(0) + ♦7(0) = 2

        rnd = _make_round([t1, t2, t3, t4, t5, t6, t7, t8])
        analysis = analyze_round_points(rnd, "SUN", None)

        assert analysis.is_complete_round is True
        total_card = analysis.raw_abnat_team_02 + analysis.raw_abnat_team_13
        assert total_card == EXPECTED_CARD_ABNAT_SUN  # 120

    def test_last_trick_bonus(self):
        """Team winning trick 8 gets +10 Abnat bonus."""
        tricks = [_make_trick(i + 1, winner_seat=0) for i in range(8)]
        rnd = _make_round(tricks)
        analysis = analyze_round_points(rnd, "SUN", None)
        assert analysis.is_complete_round is True
        assert analysis.last_trick_team == "team_02"  # seat 0 wins trick 8
        # total_02 should include raw + 10 bonus
        assert analysis.total_abnat_team_02 == analysis.raw_abnat_team_02 + LAST_TRICK_BONUS

    def test_hokum_trump_points(self):
        """HOKUM trump cards use HOKUM point values (J=20, 9=14)."""
        # ♥J(idx=22) → HOKUM trump ♥ → 20 pts
        # ♥9(idx=20) → HOKUM trump ♥ → 14 pts
        trick = _make_trick(
            1,
            cards_by_seat={0: 22, 1: 20, 2: 18, 3: 19},
            winner_seat=0,
        )
        # ♥J(20) + ♥9(14) + ♥7(0) + ♥8(0) = 34
        rnd = _make_round([trick], mode="hokom", trump=1)
        analysis = analyze_round_points(rnd, "HOKUM", "♥")
        assert analysis.raw_abnat_team_02 == 34

    def test_incomplete_round_skips_consistency(self):
        """Incomplete rounds (< 8 tricks) skip card_consistent check."""
        trick = _make_trick(1, winner_seat=0)
        rnd = _make_round([trick])
        analysis = analyze_round_points(rnd, "SUN", None)
        assert analysis.is_complete_round is False
        assert analysis.card_points_consistent is True  # Skipped


# ── analyze_session_points ───────────────────────────────────────────

class TestAnalyzeSessionPoints:

    def test_empty_extraction(self):
        extraction = ExtractionResult(session_path="empty", rounds=[])
        analyses = analyze_session_points(extraction)
        assert analyses == []

    def test_single_round(self):
        trick = _make_trick(1, winner_seat=0)
        rnd = _make_round([trick])
        extraction = ExtractionResult(
            session_path="single",
            rounds=[rnd],
            total_tricks=1,
            total_events_scanned=2,
        )
        analyses = analyze_session_points(extraction)
        assert len(analyses) == 1
        assert analyses[0].round_index == 0

    def test_multiple_rounds(self):
        """Multiple rounds analyzed independently."""
        t1 = _make_trick(1, round_index=0, winner_seat=0)
        t2 = _make_trick(1, round_index=1, winner_seat=1)
        rnd1 = _make_round([t1], round_index=0)
        rnd2 = _make_round([t2], round_index=1)
        extraction = ExtractionResult(
            session_path="multi",
            rounds=[rnd1, rnd2],
            total_tricks=2,
            total_events_scanned=4,
        )
        analyses = analyze_session_points(extraction)
        assert len(analyses) == 2
        assert analyses[0].round_index == 0
        assert analyses[1].round_index == 1
