"""
Tests for report_exporter — JSON and Markdown export.
"""
import json
import pytest
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from gbaloot.core.report_exporter import (
    session_report_to_dict,
    session_report_to_markdown,
    export_session_report,
    export_scorecard,
    export_divergences,
    list_saved_reports,
)
from gbaloot.core.comparator import TrickComparison, Divergence, ComparisonReport


# ── Fake SessionReport (avoid importing full round_report chain) ─────

@dataclass
class FakeBid:
    seat: int = 0
    action: str = "SUN"
    bidding_round: int = 1
    raw_bt: int = 1


@dataclass
class FakeBidSequence:
    round_index: int = 0
    final_mode: str = "SUN"
    caller_seat: int = 0
    dealer_seat: int = 1
    face_card_idx: int = -1
    final_trump_idx: Optional[int] = None
    bids: list = field(default_factory=list)


@dataclass
class FakePointAnalysis:
    round_index: int = 0
    is_complete_round: bool = True
    raw_abnat_team_02: int = 80
    raw_abnat_team_13: int = 46
    card_points_consistent: bool = True


@dataclass
class FakeRoundReport:
    round_index: int = 0
    game_mode: str = "SUN"
    trump_suit: Optional[str] = None
    dealer_seat: int = 0
    bid_sequence: Optional[FakeBidSequence] = None
    bid_comparison: Optional[object] = None
    trick_comparisons: list = field(default_factory=list)
    point_analysis: Optional[FakePointAnalysis] = None
    num_tricks: int = 0
    trick_agreement_pct: float = 0.0
    screenshots: list = field(default_factory=list)

    @property
    def is_complete(self):
        return self.num_tricks == 8

    @property
    def has_divergences(self):
        return any(not tc.winner_agrees for tc in self.trick_comparisons)

    @property
    def overall_status(self):
        if self.has_divergences:
            return "X"
        return "OK"


@dataclass
class FakeSessionReport:
    session_path: str = "test.json"
    generated_at: str = "2025-01-01T00:00:00"
    rounds: list = field(default_factory=list)
    total_tricks: int = 0
    total_rounds: int = 0
    trick_agreement_pct: float = 0.0
    rounds_with_bids: int = 0
    complete_rounds: int = 0
    point_consistent_rounds: int = 0
    screenshot_count: int = 0


def _tc(trick_num=1, agrees=True):
    return TrickComparison(
        trick_number=trick_num,
        round_index=0,
        cards=[{"seat": 0, "card": "A\u2660"}, {"seat": 1, "card": "K\u2665"}],
        lead_suit="\u2660",
        game_mode="SUN",
        trump_suit=None,
        source_winner_seat=0,
        engine_winner_seat=0 if agrees else 1,
        engine_points=10,
        winner_agrees=agrees,
    )


def _div(trick_num=1, desc="test"):
    return Divergence(
        id=f"div_{trick_num:04d}",
        session_path="test.json",
        round_index=0,
        trick_number=trick_num,
        divergence_type="TRICK_WINNER",
        severity="HIGH",
        game_mode="SUN",
        trump_suit=None,
        cards_played=[{"seat": 0, "card": "A\u2660"}],
        lead_suit="\u2660",
        source_result="Seat 0",
        engine_result="Seat 1",
        notes=desc,
    )


# ── session_report_to_dict ───────────────────────────────────────────

class TestSessionReportToDict:
    def test_empty_report(self):
        sr = FakeSessionReport()
        d = session_report_to_dict(sr)
        assert d["total_tricks"] == 0
        assert d["rounds"] == []
        assert "session_path" in d

    def test_with_tricks(self):
        rr = FakeRoundReport(
            num_tricks=2,
            trick_agreement_pct=50.0,
            trick_comparisons=[_tc(1, True), _tc(2, False)],
        )
        sr = FakeSessionReport(rounds=[rr], total_tricks=2, total_rounds=1)
        d = session_report_to_dict(sr)
        assert len(d["rounds"]) == 1
        assert len(d["rounds"][0]["trick_comparisons"]) == 2
        assert d["rounds"][0]["trick_comparisons"][0]["winner_agrees"] is True
        assert d["rounds"][0]["trick_comparisons"][1]["winner_agrees"] is False

    def test_with_bidding(self):
        bids = [FakeBid(seat=0, action="SUN"), FakeBid(seat=1, action="PASS")]
        seq = FakeBidSequence(bids=bids)
        rr = FakeRoundReport(bid_sequence=seq)
        sr = FakeSessionReport(rounds=[rr])
        d = session_report_to_dict(sr)
        assert "bidding" in d["rounds"][0]
        assert d["rounds"][0]["bidding"]["bid_count"] == 2

    def test_with_points(self):
        pa = FakePointAnalysis(raw_abnat_team_02=80, raw_abnat_team_13=46)
        rr = FakeRoundReport(point_analysis=pa)
        sr = FakeSessionReport(rounds=[rr])
        d = session_report_to_dict(sr)
        assert d["rounds"][0]["point_analysis"]["raw_abnat_team_02"] == 80


# ── session_report_to_markdown ───────────────────────────────────────

class TestSessionReportToMarkdown:
    def test_empty_report(self):
        sr = FakeSessionReport()
        md = session_report_to_markdown(sr)
        assert "# Session Report" in md
        assert "Total Tricks**: 0" in md

    def test_with_tricks_table(self):
        rr = FakeRoundReport(
            num_tricks=1,
            trick_comparisons=[_tc(1, True)],
        )
        sr = FakeSessionReport(rounds=[rr], total_tricks=1, total_rounds=1)
        md = session_report_to_markdown(sr)
        assert "| Trick |" in md
        assert "| 1 |" in md
        assert "OK" in md

    def test_divergence_marked(self):
        rr = FakeRoundReport(
            num_tricks=1,
            trick_comparisons=[_tc(1, False)],
        )
        sr = FakeSessionReport(rounds=[rr], total_tricks=1, total_rounds=1)
        md = session_report_to_markdown(sr)
        assert "DIVERGE" in md


# ── export_session_report ────────────────────────────────────────────

class TestExportSessionReport:
    def test_json_export(self, tmp_path):
        sr = FakeSessionReport(total_tricks=5)
        path = export_session_report(sr, tmp_path, "json")
        assert path.exists()
        assert path.suffix == ".json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["total_tricks"] == 5

    def test_markdown_export(self, tmp_path):
        sr = FakeSessionReport(total_tricks=3)
        path = export_session_report(sr, tmp_path, "markdown")
        assert path.exists()
        assert path.suffix == ".md"
        content = path.read_text(encoding="utf-8")
        assert "# Session Report" in content

    def test_creates_directory(self, tmp_path):
        nested = tmp_path / "a" / "b"
        sr = FakeSessionReport()
        path = export_session_report(sr, nested, "json")
        assert path.exists()
        assert nested.exists()


# ── export_scorecard ─────────────────────────────────────────────────

class TestExportScorecard:
    def test_basic(self, tmp_path):
        sc = {"trick_resolution": {"agreement_pct": 96.8}}
        path = export_scorecard(sc, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["trick_resolution"]["agreement_pct"] == 96.8


# ── export_divergences ───────────────────────────────────────────────

class TestExportDivergences:
    def test_basic(self, tmp_path):
        divs = [_div(1, "test1"), _div(2, "test2")]
        path = export_divergences(divs, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[0]["notes"] == "test1"

    def test_empty_list(self, tmp_path):
        path = export_divergences([], tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == []


# ── list_saved_reports ───────────────────────────────────────────────

class TestListSavedReports:
    def test_empty_dir(self, tmp_path):
        assert list_saved_reports(tmp_path) == []

    def test_nonexistent_dir(self, tmp_path):
        assert list_saved_reports(tmp_path / "nope") == []

    def test_finds_reports(self, tmp_path):
        (tmp_path / "session_report_20250101.json").write_text("{}")
        (tmp_path / "scorecard_20250101.json").write_text("{}")
        (tmp_path / "divergences_20250101.json").write_text("[]")
        (tmp_path / "session_report_20250101.md").write_text("# Report")
        entries = list_saved_reports(tmp_path)
        assert len(entries) == 4
        types = {e["type"] for e in entries}
        assert "Session Report" in types
        assert "Scorecard" in types
        assert "Divergences" in types

    def test_ignores_non_report_files(self, tmp_path):
        (tmp_path / "random.txt").write_text("hello")
        (tmp_path / "data.csv").write_text("a,b")
        assert list_saved_reports(tmp_path) == []

    def test_entry_structure(self, tmp_path):
        (tmp_path / "session_report_test.json").write_text('{"a":1}')
        entries = list_saved_reports(tmp_path)
        assert len(entries) == 1
        e = entries[0]
        assert "filename" in e
        assert "type" in e
        assert "format" in e
        assert "size_kb" in e
        assert "modified" in e
        assert e["format"] == "json"
