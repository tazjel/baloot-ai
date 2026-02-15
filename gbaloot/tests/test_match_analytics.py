"""
Tests for match_analytics — cross-session trend analysis.
"""
import pytest
from gbaloot.core.match_analytics import (
    build_match_progression,
    build_divergence_heatmap,
    analyze_trends,
    MatchProgression,
    RoundProgression,
    DivergenceHeatmap,
    HeatmapCell,
    TrendAnalysis,
)
from gbaloot.core.comparator import ComparisonReport, TrickComparison, Divergence


# ── Helpers ───────────────────────────────────────────────────────────

_div_counter = 0


def _tc(round_idx=0, trick_num=1, mode="SUN", agrees=True) -> TrickComparison:
    """Build a minimal TrickComparison with correct field names."""
    return TrickComparison(
        trick_number=trick_num,
        round_index=round_idx,
        cards=[{"seat": 0, "card": "A♠"}, {"seat": 1, "card": "K♥"}],
        lead_suit="♠",
        game_mode=mode,
        trump_suit="♠" if mode == "HOKUM" else None,
        source_winner_seat=0,
        engine_winner_seat=0 if agrees else 1,
        engine_points=10,
        winner_agrees=agrees,
        divergence_type=None if agrees else "TRICK_WINNER",
        notes="" if agrees else "winner mismatch",
    )


def _div(round_idx=0, trick_num=1, mode="SUN", desc="test") -> Divergence:
    """Build a minimal Divergence with correct field names."""
    global _div_counter
    _div_counter += 1
    return Divergence(
        id=f"div_{_div_counter:04d}",
        session_path="test_session.json",
        round_index=round_idx,
        trick_number=trick_num,
        divergence_type="TRICK_WINNER",
        severity="HIGH",
        game_mode=mode,
        trump_suit="♠" if mode == "HOKUM" else None,
        cards_played=[{"seat": 0, "card": "A♠"}],
        lead_suit="♠",
        source_result="Seat 0 wins",
        engine_result="Seat 1 wins",
        notes=desc,
    )


def _report(
    tricks: list[TrickComparison] | None = None,
    divs: list[Divergence] | None = None,
) -> ComparisonReport:
    """Build a minimal ComparisonReport with correct field names."""
    tc = tricks or []
    dv = divs or []
    agreed = sum(1 for t in tc if t.winner_agrees)
    pct = (agreed / len(tc) * 100) if tc else 0.0
    return ComparisonReport(
        session_path="test_session.json",
        generated_at="2025-01-01T00:00:00",
        rounds_compared=len(set(t.round_index for t in tc)) if tc else 0,
        total_tricks=len(tc),
        trick_comparisons=tc,
        winner_agreement_pct=pct,
        total_divergences=len(dv),
        divergence_breakdown={"TRICK_WINNER": len(dv)} if dv else {},
        engine_points_team_02=0,
        engine_points_team_13=0,
        extraction_warnings=[],
    )


# ── MatchProgression ─────────────────────────────────────────────────

class TestBuildMatchProgression:
    def test_empty_report(self):
        report = _report()
        prog = build_match_progression(report)
        assert prog.total_tricks == 0
        assert prog.rounds == []

    def test_single_round(self):
        tricks = [
            _tc(0, 1, "SUN", True),
            _tc(0, 2, "SUN", True),
            _tc(0, 3, "SUN", False),
        ]
        prog = build_match_progression(_report(tricks))
        assert len(prog.rounds) == 1
        assert prog.rounds[0].tricks_played == 3
        assert prog.rounds[0].tricks_agreed == 2
        assert prog.rounds[0].agreement_pct == pytest.approx(66.67, abs=0.1)

    def test_multiple_rounds(self):
        tricks = [
            _tc(0, 1, "SUN", True),
            _tc(0, 2, "SUN", True),
            _tc(1, 1, "HOKUM", False),
            _tc(1, 2, "HOKUM", True),
        ]
        prog = build_match_progression(_report(tricks))
        assert len(prog.rounds) == 2
        assert prog.total_tricks == 4
        assert prog.total_agreed == 3
        assert prog.overall_agreement == 75.0

    def test_round_mode_preserved(self):
        tricks = [_tc(0, 1, "HOKUM", True)]
        prog = build_match_progression(_report(tricks))
        assert prog.rounds[0].mode == "HOKUM"

    def test_100_percent_agreement(self):
        tricks = [_tc(0, i, "SUN", True) for i in range(1, 9)]
        prog = build_match_progression(_report(tricks))
        assert prog.overall_agreement == 100.0


# ── DivergenceHeatmap ────────────────────────────────────────────────

class TestBuildDivergenceHeatmap:
    def test_empty_divergences(self):
        hm = build_divergence_heatmap([])
        assert hm.cells == []
        assert hm.max_trick_position == 0

    def test_single_divergence(self):
        divs = [_div(0, 3, "SUN")]
        hm = build_divergence_heatmap(divs)
        assert len(hm.cells) == 1
        assert hm.cells[0].trick_position == 3
        assert hm.cells[0].mode == "SUN"
        assert hm.max_trick_position == 3

    def test_multiple_divergences_same_cell(self):
        divs = [_div(0, 1, "SUN"), _div(1, 1, "SUN")]
        hm = build_divergence_heatmap(divs)
        assert len(hm.cells) == 1
        assert hm.cells[0].divergence_count == 2

    def test_modes_detected(self):
        divs = [_div(0, 1, "SUN"), _div(0, 1, "HOKUM")]
        hm = build_divergence_heatmap(divs)
        assert "SUN" in hm.modes
        assert "HOKUM" in hm.modes

    def test_rate_with_totals(self):
        divs = [_div(0, 1, "SUN")]
        tcs = [_tc(0, 1, "SUN", True), _tc(0, 1, "SUN", False)]
        hm = build_divergence_heatmap(divs, tcs)
        assert hm.cells[0].total_tricks == 2
        assert hm.cells[0].divergence_rate == 0.5


# ── TrendAnalysis ────────────────────────────────────────────────────

class TestAnalyzeTrends:
    def test_empty_reports(self):
        trends = analyze_trends([])
        assert trends.sessions_analyzed == 0
        assert trends.total_tricks == 0

    def test_single_session(self):
        tricks = [_tc(0, 1, "SUN", True), _tc(0, 2, "SUN", False)]
        divs = [_div(0, 2, "SUN", "winner mismatch")]
        trends = analyze_trends([_report(tricks, divs)], divs)
        assert trends.sessions_analyzed == 1
        assert trends.total_tricks == 2
        assert trends.total_divergences == 1
        assert trends.per_mode_accuracy["SUN"] == 50.0

    def test_multi_session(self):
        r1 = _report([_tc(0, 1, "SUN", True)])
        r2 = _report([_tc(0, 1, "HOKUM", True)])
        trends = analyze_trends([r1, r2])
        assert trends.sessions_analyzed == 2
        assert trends.total_tricks == 2
        assert "SUN" in trends.per_mode_accuracy
        assert "HOKUM" in trends.per_mode_accuracy

    def test_top_patterns(self):
        divs = [
            _div(0, 1, "SUN", "winner mismatch"),
            _div(0, 2, "SUN", "winner mismatch"),
            _div(0, 3, "SUN", "card order diff"),
        ]
        trends = analyze_trends([_report([], divs)], divs)
        assert len(trends.top_divergence_patterns) >= 1

    def test_per_mode_count(self):
        tricks = [_tc(0, 1, "SUN", True), _tc(0, 1, "HOKUM", True)] * 3
        trends = analyze_trends([_report(tricks)])
        assert trends.per_mode_count["SUN"] == 3
        assert trends.per_mode_count["HOKUM"] == 3


# ── Dataclass defaults ────────────────────────────────────────────────

class TestDataclassDefaults:
    def test_round_progression_defaults(self):
        rp = RoundProgression()
        assert rp.round_index == 0
        assert rp.agreement_pct == 0.0

    def test_match_progression_defaults(self):
        mp = MatchProgression()
        assert mp.total_tricks == 0

    def test_heatmap_cell_defaults(self):
        hc = HeatmapCell()
        assert hc.divergence_rate == 0.0

    def test_divergence_heatmap_defaults(self):
        dh = DivergenceHeatmap()
        assert dh.max_trick_position == 0

    def test_trend_analysis_defaults(self):
        ta = TrendAnalysis()
        assert ta.sessions_analyzed == 0
