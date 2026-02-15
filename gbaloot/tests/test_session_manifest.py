"""
Tests for session_manifest — session health index and persistence.
"""
import json
import pytest
from pathlib import Path

from gbaloot.core.session_manifest import (
    SessionEntry,
    Manifest,
    classify_health,
    build_manifest,
    save_manifest,
    load_manifest,
    get_sessions_by_health,
    get_entry_by_filename,
    HEALTH_ICONS,
    MANIFEST_FILENAME,
)


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_session_json(
    path: Path,
    *,
    label: str = "",
    events: list | None = None,
) -> Path:
    """Write a minimal processed session JSON file."""
    data = {
        "capture_path": str(path),
        "label": label,
        "stats": {},
        "events": events or [],
        "timeline": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def _gs_event(inner: dict, action: str = "game_state") -> dict:
    """Build a serialized game_state event dict."""
    return {
        "timestamp": 1000,
        "direction": "RECV",
        "action": action,
        "fields": {"p": {"p": inner, "c": "game_state"}, "a": 13},
        "raw_size": 100,
        "decode_errors": [],
    }


def _non_gs_event(action: str = "ws_connect") -> dict:
    return {
        "timestamp": 500,
        "direction": "RECV",
        "action": action,
        "fields": {"info": "connected"},
        "raw_size": 20,
        "decode_errors": [],
    }


# ── Health Classification ─────────────────────────────────────────────

class TestClassifyHealth:
    def test_good_with_tricks(self):
        entry = SessionEntry(filename="a.json", has_tricks=True, trick_count=5, game_event_count=10)
        assert classify_health(entry) == "good"

    def test_partial_with_game_events_no_tricks(self):
        entry = SessionEntry(filename="b.json", has_tricks=False, trick_count=0, game_event_count=10)
        assert classify_health(entry) == "partial"

    def test_empty_with_no_game_events(self):
        entry = SessionEntry(filename="c.json", has_tricks=False, trick_count=0, game_event_count=0)
        assert classify_health(entry) == "empty"

    def test_good_requires_positive_trick_count(self):
        entry = SessionEntry(filename="d.json", has_tricks=True, trick_count=0, game_event_count=5)
        # has_tricks True but trick_count 0 is contradictory; classify_health checks both
        assert classify_health(entry) == "partial"


class TestHealthIcons:
    def test_all_health_levels_have_icons(self):
        for level in ("good", "partial", "empty"):
            assert level in HEALTH_ICONS


# ── SessionEntry ──────────────────────────────────────────────────────

class TestSessionEntry:
    def test_defaults(self):
        e = SessionEntry(filename="test.json")
        assert e.health == "empty"
        assert e.trick_count == 0
        assert e.has_bids is False

    def test_to_dict_roundtrip(self):
        e = SessionEntry(
            filename="test.json",
            label="my session",
            has_tricks=True,
            trick_count=12,
            health="good",
        )
        d = e.to_dict()
        e2 = SessionEntry(**d)
        assert e2.filename == e.filename
        assert e2.trick_count == 12
        assert e2.health == "good"


# ── Manifest ──────────────────────────────────────────────────────────

class TestManifest:
    def test_empty_manifest(self):
        m = Manifest()
        assert m.total_sessions == 0
        assert len(m.entries) == 0

    def test_to_dict(self):
        m = Manifest(
            entries=[SessionEntry(filename="a.json", health="good")],
            total_sessions=1,
            good_count=1,
        )
        d = m.to_dict()
        assert d["total_sessions"] == 1
        assert len(d["entries"]) == 1
        assert d["entries"][0]["filename"] == "a.json"


# ── Build Manifest (filesystem) ──────────────────────────────────────

class TestBuildManifest:
    def test_empty_directory(self, tmp_path):
        m = build_manifest(tmp_path)
        assert m.total_sessions == 0

    def test_nonexistent_directory(self, tmp_path):
        m = build_manifest(tmp_path / "nope")
        assert m.total_sessions == 0

    def test_session_with_no_game_events(self, tmp_path):
        _make_session_json(
            tmp_path / "empty_processed.json",
            events=[_non_gs_event()],
        )
        m = build_manifest(tmp_path)
        assert m.total_sessions == 1
        assert m.empty_count == 1
        assert m.entries[0].health == "empty"

    def test_session_with_game_events_no_tricks(self, tmp_path):
        _make_session_json(
            tmp_path / "partial_processed.json",
            events=[
                _gs_event({"gStg": 1, "pcsCount": [8, 8, 8, 8]}),
                _gs_event({"gStg": 2, "played_cards": [-1, -1, -1, -1]}),
            ],
        )
        m = build_manifest(tmp_path)
        assert m.total_sessions == 1
        assert m.partial_count == 1
        assert m.entries[0].game_event_count == 2

    def test_session_with_complete_tricks(self, tmp_path):
        _make_session_json(
            tmp_path / "good_processed.json",
            events=[
                _gs_event({
                    "gStg": 3,
                    "played_cards": [5, 18, 31, 44],
                    "rb": 1,
                }),
                _gs_event({
                    "gStg": 3,
                    "played_cards": [6, 19, 32, 45],
                    "rb": 1,
                }),
            ],
        )
        m = build_manifest(tmp_path)
        assert m.total_sessions == 1
        assert m.good_count == 1
        assert m.entries[0].trick_count == 2
        assert m.entries[0].round_count == 1

    def test_session_detects_bids(self, tmp_path):
        _make_session_json(
            tmp_path / "bids_processed.json",
            events=[
                _gs_event({
                    "gStg": 1,
                    "pcsCount": [8, 8, 8, 8],
                    "last_action": {"action": "a_bid", "ap": 1, "bt": "hokom1"},
                }),
            ],
        )
        m = build_manifest(tmp_path)
        assert m.entries[0].has_bids is True

    def test_multiple_sessions_health_counts(self, tmp_path):
        _make_session_json(tmp_path / "a_processed.json", events=[_non_gs_event()])
        _make_session_json(
            tmp_path / "b_processed.json",
            events=[_gs_event({"pcsCount": [8, 8, 8, 8]})],
        )
        _make_session_json(
            tmp_path / "c_processed.json",
            events=[_gs_event({"played_cards": [5, 18, 31, 44], "rb": 1})],
        )
        m = build_manifest(tmp_path)
        assert m.total_sessions == 3
        assert m.good_count == 1
        assert m.partial_count == 1
        assert m.empty_count == 1

    def test_corrupted_json_handled(self, tmp_path):
        bad_file = tmp_path / "bad_processed.json"
        bad_file.write_text("{invalid json!!!", encoding="utf-8")
        m = build_manifest(tmp_path)
        assert m.total_sessions == 1
        assert m.entries[0].health == "empty"

    def test_session_with_multiple_rounds(self, tmp_path):
        _make_session_json(
            tmp_path / "multi_processed.json",
            events=[
                _gs_event({"played_cards": [5, 18, 31, 44], "rb": 1}),
                _gs_event({"played_cards": [6, 19, 32, 45], "rb": 2}),
                _gs_event({"played_cards": [7, 20, 33, 46], "rb": 3}),
            ],
        )
        m = build_manifest(tmp_path)
        assert m.entries[0].round_count == 3


# ── Save / Load Manifest ─────────────────────────────────────────────

class TestSaveLoad:
    def test_save_creates_file(self, tmp_path):
        m = Manifest(
            entries=[SessionEntry(filename="x.json", health="good", trick_count=5)],
            total_sessions=1,
            good_count=1,
        )
        out = save_manifest(m, tmp_path)
        assert out.exists()
        assert out.name == MANIFEST_FILENAME

    def test_load_roundtrip(self, tmp_path):
        m = Manifest(
            entries=[
                SessionEntry(filename="a.json", health="good", trick_count=10, has_bids=True),
                SessionEntry(filename="b.json", health="empty"),
            ],
            total_sessions=2,
            good_count=1,
            empty_count=1,
        )
        save_manifest(m, tmp_path)
        loaded = load_manifest(tmp_path)
        assert loaded is not None
        assert loaded.total_sessions == 2
        assert loaded.entries[0].trick_count == 10
        assert loaded.entries[1].health == "empty"

    def test_load_missing_returns_none(self, tmp_path):
        assert load_manifest(tmp_path) is None

    def test_load_corrupted_returns_none(self, tmp_path):
        (tmp_path / MANIFEST_FILENAME).write_text("not json", encoding="utf-8")
        assert load_manifest(tmp_path) is None


# ── Filtering ─────────────────────────────────────────────────────────

class TestFiltering:
    def _sample_manifest(self) -> Manifest:
        return Manifest(
            entries=[
                SessionEntry(filename="a.json", health="good"),
                SessionEntry(filename="b.json", health="partial"),
                SessionEntry(filename="c.json", health="good"),
                SessionEntry(filename="d.json", health="empty"),
            ],
            total_sessions=4,
            good_count=2,
            partial_count=1,
            empty_count=1,
        )

    def test_filter_good(self):
        m = self._sample_manifest()
        good = get_sessions_by_health(m, "good")
        assert len(good) == 2
        assert all(e.health == "good" for e in good)

    def test_filter_empty(self):
        m = self._sample_manifest()
        empty = get_sessions_by_health(m, "empty")
        assert len(empty) == 1

    def test_filter_returns_empty_list_for_unknown(self):
        m = self._sample_manifest()
        assert get_sessions_by_health(m, "unknown") == []

    def test_get_entry_by_filename(self):
        m = self._sample_manifest()
        entry = get_entry_by_filename(m, "b.json")
        assert entry is not None
        assert entry.health == "partial"

    def test_get_entry_missing(self):
        m = self._sample_manifest()
        assert get_entry_by_filename(m, "nope.json") is None
