"""Tests for the Kammelna mobile archive parser."""
from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path

from gbaloot.tools.archive_parser import (
    parse_archive,
    load_all_archives,
    ArchiveGame,
    ArchiveRound,
    ARCHIVE_GM_TO_MODE,
    ARCHIVE_TS_TO_SUIT_IDX,
    _resolve_bidding,
    _extract_round_result,
)


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_archive(rounds=None, **overrides):
    """Create a minimal valid archive dict."""
    data = {
        "v": 1,
        "n": "Test Session",
        "ps": [100, 200, 300, 400],
        "psN": ["Alice", "Bob", "Charlie", "Dave"],
        "psRP": [10, 20, 30, 40],
        "psRN": [1, 1, 1, 1],
        "psCb": [0, 0, 0, 0],
        "psV": [0, 0, 0, 0],
        "psSb": [0, 0, 0, 0],
        "rL": 1,
        "Id": 12345,
        "t": 1,
        "chA": 1,
        "gT": 1,
        "pT": 1700000000000,
        "s1": 100,
        "s2": 80,
        "rs": rounds or [],
    }
    data.update(overrides)
    return data


def _write_archive(data, tmp_path):
    """Write archive data to a temp JSON file and return the path."""
    fpath = tmp_path / "test_session.json"
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return fpath


def _make_round_events(mode="HOKUM", trump_bid="hokom", fc_idx=44):
    """Build a minimal round with bidding and one trick."""
    events = [
        {"e": 15, "bhr": [0, 0, 0, 0], "fhr": [0, 0, 0, 0]},
        {"p": 1, "e": 1, "fc": fc_idx},
    ]
    # Bidding
    gm = 2 if mode == "HOKUM" else (1 if mode == "SUN" else 3)
    events.append({"p": 1, "e": 2, "b": "pass", "ts": 4, "rb": -1})
    events.append({"p": 2, "e": 2, "b": trump_bid, "gm": gm, "ts": 4, "rb": 2})
    events.append({"p": 3, "e": 2, "b": "pass", "gm": gm, "ts": 4, "rb": 2})
    events.append({"p": 4, "e": 2, "b": "pass", "gm": gm, "ts": 4, "rb": 2})
    # One trick: all spades
    events.append({"p": 1, "e": 4, "c": 12})  # A♠
    events.append({"p": 2, "e": 4, "c": 11})  # K♠
    events.append({"p": 3, "e": 4, "c": 10})  # Q♠
    events.append({"p": 4, "e": 4, "c": 9})   # J♠
    events.append({"p": 1, "e": 6})  # trick boundary
    # Round result
    events.append({
        "e": 12,
        "rs": {"p1": 20, "p2": 0, "lmw": 1, "m": gm, "r1": [], "r2": [],
               "e1": 20, "e2": 0, "w": 1, "s1": 20, "s2": 0, "b": 1},
    })
    return events


# ── Tests: Top-Level Parsing ────────────────────────────────────────

class TestParseArchive:
    """Test parse_archive() with synthetic data."""

    def test_parses_metadata(self, tmp_path):
        data = _make_archive(s1=100, s2=80, n="جلسة 5")
        fpath = _write_archive(data, tmp_path)

        game = parse_archive(fpath)

        assert game.version == 1
        assert game.session_name == "جلسة 5"
        assert game.session_id == 12345
        assert game.player_names == ["Alice", "Bob", "Charlie", "Dave"]
        assert game.player_ids == [100, 200, 300, 400]
        assert game.final_score_team1 == 100
        assert game.final_score_team2 == 80

    def test_parses_rounds(self, tmp_path):
        events = _make_round_events(mode="HOKUM")
        data = _make_archive(rounds=[{"r": events}])
        fpath = _write_archive(data, tmp_path)

        game = parse_archive(fpath)

        assert len(game.rounds) == 1
        rnd = game.rounds[0]
        assert rnd.round_index == 0
        assert rnd.game_mode == "HOKUM"
        assert rnd.bidder_seat == 1  # P2 bid -> 0-indexed seat 1

    def test_empty_rounds(self, tmp_path):
        data = _make_archive(rounds=[])
        fpath = _write_archive(data, tmp_path)

        game = parse_archive(fpath)
        assert len(game.rounds) == 0

    def test_missing_rs_raises(self, tmp_path):
        data = {"v": 1, "n": "test"}
        fpath = _write_archive(data, tmp_path)

        with pytest.raises(ValueError, match="Missing 'rs'"):
            parse_archive(fpath)

    def test_invalid_json_raises(self, tmp_path):
        fpath = tmp_path / "bad.json"
        fpath.write_text("not json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            parse_archive(fpath)

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_archive(tmp_path / "nonexistent.json")


# ── Tests: Mode Resolution ──────────────────────────────────────────

class TestModeResolution:
    """Test game mode and trump suit parsing from bid events."""

    def test_hokum_mode(self, tmp_path):
        events = _make_round_events(mode="HOKUM")
        data = _make_archive(rounds=[{"r": events}])
        fpath = _write_archive(data, tmp_path)

        game = parse_archive(fpath)
        assert game.rounds[0].game_mode == "HOKUM"

    def test_sun_mode(self, tmp_path):
        events = _make_round_events(mode="SUN", trump_bid="sun")
        data = _make_archive(rounds=[{"r": events}])
        fpath = _write_archive(data, tmp_path)

        game = parse_archive(fpath)
        assert game.rounds[0].game_mode == "SUN"

    def test_ashkal_mode_maps_to_sun(self, tmp_path):
        events = _make_round_events(mode="SUN", trump_bid="ashkal")
        # Override gm to 3
        for evt in events:
            if evt.get("e") == 2 and evt.get("gm") is not None:
                evt["gm"] = 3
        data = _make_archive(rounds=[{"r": events}])
        fpath = _write_archive(data, tmp_path)

        game = parse_archive(fpath)
        assert game.rounds[0].game_mode == "SUN"

    def test_gm3_in_mode_map(self):
        assert ARCHIVE_GM_TO_MODE[3] == "SUN"

    def test_no_bid_warns(self):
        events = [
            {"e": 15, "bhr": [0], "fhr": [0]},
            {"p": 1, "e": 1, "fc": 44},
            {"p": 1, "e": 2, "b": "pass", "ts": 4, "rb": -1},
        ]
        warnings: list[str] = []
        mode, trump, bidder = _resolve_bidding(events, 0, warnings)
        assert mode is None
        assert len(warnings) == 1
        assert "no gm found" in warnings[0]


# ── Tests: Trump Suit Mapping ───────────────────────────────────────

class TestTrumpSuitMapping:
    """Test archive trump suit index mapping."""

    def test_ts_mapping_values(self):
        assert ARCHIVE_TS_TO_SUIT_IDX[1] == 0   # spade
        assert ARCHIVE_TS_TO_SUIT_IDX[2] == 2   # clubs
        assert ARCHIVE_TS_TO_SUIT_IDX[3] == 3   # diamonds
        assert ARCHIVE_TS_TO_SUIT_IDX[4] == 1   # hearts


# ── Tests: Round Result Extraction ──────────────────────────────────

class TestRoundResult:
    """Test round result parsing."""

    def test_extracts_result(self):
        events = [
            {"e": 4, "p": 1, "c": 12},
            {"e": 12, "rs": {"w": 1, "e1": 50, "e2": 70, "s1": 50, "s2": 70}},
        ]
        result = _extract_round_result(events)
        assert result is not None
        assert result["w"] == 1
        assert result["e1"] == 50

    def test_no_result_returns_none(self):
        events = [{"e": 4, "p": 1, "c": 12}]
        assert _extract_round_result(events) is None


# ── Tests: Load All Archives ────────────────────────────────────────

class TestLoadAllArchives:
    """Test batch loading of archive files."""

    def test_loads_multiple(self, tmp_path):
        for i in range(3):
            data = _make_archive(n=f"Session {i}", Id=i)
            fpath = tmp_path / f"session_{i}.json"
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f)

        games = load_all_archives(tmp_path)
        assert len(games) == 3

    def test_skips_bad_files(self, tmp_path):
        # One good file
        good = _make_archive(n="Good")
        with open(tmp_path / "good.json", "w", encoding="utf-8") as f:
            json.dump(good, f)
        # One bad file
        with open(tmp_path / "bad.json", "w", encoding="utf-8") as f:
            f.write("not valid json")

        games = load_all_archives(tmp_path)
        assert len(games) == 1
        assert games[0].session_name == "Good"
