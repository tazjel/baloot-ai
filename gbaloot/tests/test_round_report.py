"""
Tests for unified round report (gbaloot.core.round_report) and
screenshot correlation (gbaloot.tools.screenshot_diff).

Covers: RoundReport properties, SessionReport aggregation,
build_session_report orchestration, screenshot timestamp parsing,
and event correlation.
"""
import pytest
from pathlib import Path

from gbaloot.core.round_report import (
    RoundReport,
    SessionReport,
    build_session_report,
)
from gbaloot.core.comparator import TrickComparison
from gbaloot.core.bid_extractor import ExtractedBid, ExtractedBidSequence
from gbaloot.core.point_tracker import PointAnalysis
from gbaloot.core.trick_extractor import (
    ExtractedTrick,
    ExtractedRound,
    ExtractionResult,
)
from gbaloot.tools.screenshot_diff import (
    _parse_screenshot_timestamp,
    _parse_screenshot_reason,
    correlate_screenshots_with_events,
)


# ── Helpers ─────────────────────────────────────────────────────────

def _make_trick_comparison(
    trick_number: int = 1,
    round_index: int = 0,
    winner_agrees: bool = True,
    engine_points: int = 10,
    game_mode: str = "SUN",
) -> TrickComparison:
    """Build a TrickComparison for testing."""
    return TrickComparison(
        trick_number=trick_number,
        round_index=round_index,
        cards=[
            {"seat": 0, "index": 12, "card": "A♠", "points": 11},
            {"seat": 1, "index": 8, "card": "10♠", "points": 10},
            {"seat": 2, "index": 11, "card": "K♠", "points": 4},
            {"seat": 3, "index": 10, "card": "Q♠", "points": 3},
        ],
        lead_suit="♠",
        game_mode=game_mode,
        trump_suit=None,
        source_winner_seat=0,
        engine_winner_seat=0 if winner_agrees else 1,
        engine_points=engine_points,
        winner_agrees=winner_agrees,
    )


def _make_bid_sequence(
    round_index: int = 0,
    final_mode: str = "SUN",
    num_bids: int = 3,
) -> ExtractedBidSequence:
    """Build an ExtractedBidSequence for testing."""
    bids = []
    for i in range(num_bids):
        bids.append(ExtractedBid(
            seat=i % 4,
            action="PASS" if i < num_bids - 1 else final_mode,
            raw_bt="pass" if i < num_bids - 1 else final_mode.lower(),
            bidding_round=1,
            timestamp=1000.0 + i * 100,
        ))
    return ExtractedBidSequence(
        round_index=round_index,
        bids=bids,
        final_mode=final_mode,
        dealer_seat=0,
        caller_seat=bids[-1].seat,
    )


def _make_point_analysis(
    round_index: int = 0,
    is_complete: bool = True,
    card_consistent: bool = True,
) -> PointAnalysis:
    """Build a PointAnalysis for testing."""
    return PointAnalysis(
        round_index=round_index,
        game_mode="SUN",
        raw_abnat_team_02=70,
        raw_abnat_team_13=50,
        last_trick_team="team_02",
        total_abnat_team_02=80,
        total_abnat_team_13=50,
        gp_team_02=16,
        gp_team_13=10,
        card_points_consistent=card_consistent,
        gp_sum_matches_target=True,
        is_complete_round=is_complete,
    )


# ── RoundReport Properties ──────────────────────────────────────────

class TestRoundReportProperties:

    def test_is_complete_with_8_tricks(self):
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            num_tricks=8,
        )
        assert rr.is_complete is True

    def test_is_complete_with_fewer_tricks(self):
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            num_tricks=5,
        )
        assert rr.is_complete is False

    def test_has_divergences_when_tricks_disagree(self):
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            trick_comparisons=[
                _make_trick_comparison(winner_agrees=True),
                _make_trick_comparison(trick_number=2, winner_agrees=False),
            ],
        )
        assert rr.has_divergences is True

    def test_no_divergences_when_all_agree(self):
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            trick_comparisons=[
                _make_trick_comparison(winner_agrees=True),
                _make_trick_comparison(trick_number=2, winner_agrees=True),
            ],
        )
        assert rr.has_divergences is False

    def test_has_bidding_with_bids(self):
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            bid_sequence=_make_bid_sequence(),
        )
        assert rr.has_bidding is True

    def test_has_bidding_without_bids(self):
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
        )
        assert rr.has_bidding is False

    def test_has_bidding_empty_bids(self):
        """Bid sequence with zero bids counts as no bidding."""
        empty_seq = ExtractedBidSequence(round_index=0, bids=[])
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            bid_sequence=empty_seq,
        )
        assert rr.has_bidding is False

    def test_has_points(self):
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            point_analysis=_make_point_analysis(),
        )
        assert rr.has_points is True

    def test_overall_status_ok(self):
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            trick_comparisons=[_make_trick_comparison(winner_agrees=True)],
        )
        assert rr.overall_status == "✅"

    def test_overall_status_divergence(self):
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            trick_comparisons=[_make_trick_comparison(winner_agrees=False)],
        )
        assert rr.overall_status == "❌"

    def test_overall_status_point_warning(self):
        """Complete round with inconsistent points shows warning."""
        rr = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            num_tricks=8,
            trick_comparisons=[_make_trick_comparison(winner_agrees=True)],
            point_analysis=_make_point_analysis(card_consistent=False),
        )
        assert rr.overall_status == "⚠️"


# ── SessionReport ───────────────────────────────────────────────────

class TestSessionReport:

    def test_empty_session_report(self):
        sr = SessionReport(
            session_path="test",
            generated_at="2024-01-01",
        )
        assert sr.total_tricks == 0
        assert sr.total_rounds == 0
        assert sr.rounds == []

    def test_session_report_with_rounds(self):
        rr1 = RoundReport(
            round_index=0, game_mode="SUN", trump_suit=None, dealer_seat=0,
            num_tricks=8, bid_sequence=_make_bid_sequence(),
            point_analysis=_make_point_analysis(card_consistent=True),
        )
        rr2 = RoundReport(
            round_index=1, game_mode="HOKUM", trump_suit="♥", dealer_seat=1,
            num_tricks=3,
        )
        sr = SessionReport(
            session_path="test",
            generated_at="2024-01-01",
            rounds=[rr1, rr2],
            total_tricks=11,
            total_rounds=2,
            rounds_with_bids=1,
            complete_rounds=1,
            point_consistent_rounds=1,
        )
        assert sr.total_rounds == 2
        assert sr.rounds_with_bids == 1
        assert sr.complete_rounds == 1
        assert sr.point_consistent_rounds == 1


# ── build_session_report ────────────────────────────────────────────

class TestBuildSessionReport:

    def test_empty_events(self):
        sr = build_session_report([], "empty")
        assert sr.total_tricks == 0
        assert sr.total_rounds == 0
        assert sr.rounds == []

    def test_report_has_comparison(self):
        """Even with no tricks, the comparison report should be present."""
        sr = build_session_report([], "no_data")
        assert sr.comparison_report is not None

    def test_report_has_bid_result(self):
        """Bid extraction should run even on empty events."""
        sr = build_session_report([], "no_data")
        assert sr.bid_result is not None
        assert sr.bid_result.total_bids == 0


# ── Screenshot Timestamp Parsing ────────────────────────────────────

class TestScreenshotTimestampParsing:

    def test_standard_filename(self):
        ts = _parse_screenshot_timestamp("ss_mygame_periodic_1707000000000.png")
        assert ts == 1707000000000.0

    def test_epoch_seconds_converted(self):
        """Epoch seconds (< 1 trillion) should be converted to ms."""
        ts = _parse_screenshot_timestamp("screenshot_1707000000.png")
        assert ts == 1707000000000.0

    def test_no_timestamp(self):
        ts = _parse_screenshot_timestamp("random_image.png")
        assert ts == 0.0

    def test_multiple_numeric_parts(self):
        """Should use the last numeric part as timestamp."""
        ts = _parse_screenshot_timestamp("ss_game01_a_card_played_1707000000000.png")
        assert ts == 1707000000000.0


class TestScreenshotReasonParsing:

    def test_standard_reason(self):
        reason = _parse_screenshot_reason("ss_mygame_periodic_1707000000000.png")
        assert reason == "periodic"

    def test_compound_reason(self):
        reason = _parse_screenshot_reason("ss_mygame_a_card_played_1707000000000.png")
        assert reason == "a_card_played"

    def test_unknown_format(self):
        reason = _parse_screenshot_reason("random_image.png")
        assert reason == "unknown"


# ── Screenshot Correlation ──────────────────────────────────────────

class TestCorrelateScreenshots:

    def test_nonexistent_directory(self):
        result = correlate_screenshots_with_events(
            Path("/nonexistent/dir"),
            ExtractionResult(session_path="test"),
        )
        assert result == []

    def test_empty_extraction(self, tmp_path):
        """Screenshots with no trick data are assigned round -1."""
        ss_dir = tmp_path / "screenshots"
        ss_dir.mkdir()
        (ss_dir / "ss_test_periodic_1000.png").write_bytes(b"fake_png")

        extraction = ExtractionResult(session_path="test")
        result = correlate_screenshots_with_events(ss_dir, extraction)
        assert len(result) == 1
        assert result[0]["round_index"] == -1

    def test_correlation_matches_closest(self, tmp_path):
        """Screenshot should be matched to closest trick by timestamp."""
        ss_dir = tmp_path / "screenshots"
        ss_dir.mkdir()
        # Screenshot at ts=1500 — should match trick at ts=1200 (closer) not ts=2000
        (ss_dir / "ss_test_periodic_1500.png").write_bytes(b"fake_png")

        trick1 = ExtractedTrick(
            trick_number=1, round_index=0, cards_by_seat={0: 5, 1: 6, 2: 7, 3: 8},
            winner_seat=0, lead_suit_idx=0, game_mode_raw="ashkal",
            trump_suit_idx=None, scores_snapshot=[6, 6, 6, 6], timestamp=1200.0,
        )
        trick2 = ExtractedTrick(
            trick_number=2, round_index=0, cards_by_seat={0: 5, 1: 6, 2: 7, 3: 8},
            winner_seat=0, lead_suit_idx=0, game_mode_raw="ashkal",
            trump_suit_idx=None, scores_snapshot=[6, 6, 6, 6], timestamp=2000.0,
        )
        rnd = ExtractedRound(
            round_index=0, game_mode_raw="ashkal", trump_suit_idx=None,
            dealer_seat=0, tricks=[trick1, trick2],
        )
        extraction = ExtractionResult(
            session_path="test", rounds=[rnd], total_tricks=2,
        )
        result = correlate_screenshots_with_events(ss_dir, extraction)
        assert len(result) == 1
        # Screenshot at 1500ms is closer to trick1 at 1200ms (delta=300)
        # than trick2 at 2000ms (delta=500)
        assert result[0]["trick_number"] == 1
        assert result[0]["round_index"] == 0
