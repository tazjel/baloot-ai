"""
Tests for GBaloot data models.
"""
import json
import pytest
from pathlib import Path

from gbaloot.core.models import (
    GameEvent,
    PlayerState,
    BoardState,
    CaptureSession,
    ProcessedSession,
    GameTask,
    TaskStore,
)


# ── GameEvent ─────────────────────────────────────────────────────────

class TestGameEvent:
    def test_construction(self):
        ev = GameEvent(
            timestamp=1000.0,
            direction="RECV",
            action="game_state",
            fields={"key": "value"},
        )
        assert ev.timestamp == 1000.0
        assert ev.action == "game_state"
        assert ev.raw_size == 0
        assert ev.decode_errors == []

    def test_decode_errors_default(self):
        ev = GameEvent(1, "RECV", "test", {})
        assert isinstance(ev.decode_errors, list)


# ── PlayerState ───────────────────────────────────────────────────────

class TestPlayerState:
    def test_defaults(self):
        ps = PlayerState()
        assert ps.seat == -1
        assert ps.name == "Unknown"
        assert ps.hand == []
        assert ps.cards_remaining == 0

    def test_id_compat_property(self):
        ps = PlayerState(seat=2)
        assert ps.id == 2

    def test_hand_mutable(self):
        ps = PlayerState()
        ps.hand.append("A♠")
        assert "A♠" in ps.hand


# ── BoardState ────────────────────────────────────────────────────────

class TestBoardState:
    def test_defaults(self):
        bs = BoardState()
        assert bs.phase == "WAITING"
        assert bs.game_mode == ""
        assert bs.trump_suit is None
        assert bs.scores == [0, 0, 0, 0]

    def test_center_cards_as_tuples(self):
        bs = BoardState(center_cards=[(0, "A♠"), (1, "K♥")])
        assert len(bs.center_cards) == 2
        assert bs.center_cards[0] == (0, "A♠")

    def test_to_dict_center_cards_as_lists(self):
        bs = BoardState(center_cards=[(0, "A♠")])
        d = bs.to_dict()
        assert d["center_cards"] == [[0, "A♠"]]

    def test_compat_properties(self):
        bs = BoardState(
            current_player_seat=2,
            dealer_seat=3,
            last_action_desc="played",
            game_mode="HOKUM",
        )
        assert bs.current_player_id == 2
        assert bs.dealer_id == 3
        assert bs.last_action == "played"
        assert bs.contract == "HOKUM"

    def test_contract_none_when_empty(self):
        bs = BoardState(game_mode="")
        assert bs.contract is None

    def test_bidding_history_default(self):
        bs = BoardState()
        assert bs.bidding_history == []


# ── CaptureSession ────────────────────────────────────────────────────

class TestCaptureSession:
    def test_construction(self):
        cs = CaptureSession(file_path="/tmp/test.json")
        assert cs.file_path == "/tmp/test.json"
        assert cs.ws_count == 0
        assert cs.tags == []

    def test_to_dict(self):
        cs = CaptureSession(file_path="/tmp/test.json", label="test")
        d = cs.to_dict()
        assert d["label"] == "test"
        assert "file_path" in d


# ── ProcessedSession ─────────────────────────────────────────────────

class TestProcessedSession:
    def test_construction(self):
        ps = ProcessedSession(capture_path="/tmp/test.json")
        assert ps.events == []
        assert ps.stats == {}

    def test_save_and_load(self, tmp_path):
        ps = ProcessedSession(
            capture_path="/tmp/test.json",
            label="test session",
            stats={"total": 10},
            events=[{"action": "game_state", "timestamp": 1000}],
        )
        out = ps.save(tmp_path)
        assert out.exists()
        assert out.name.endswith("_processed.json")

        loaded = ProcessedSession.load(out)
        assert loaded.label == "test session"
        assert loaded.stats["total"] == 10
        assert len(loaded.events) == 1

    def test_to_dict(self):
        ps = ProcessedSession(capture_path="/tmp/test.json", label="x")
        d = ps.to_dict()
        assert d["label"] == "x"


# ── GameTask ──────────────────────────────────────────────────────────

class TestGameTask:
    def test_defaults(self):
        t = GameTask()
        assert t.status == "todo"
        assert t.priority == "medium"

    def test_to_dict(self):
        t = GameTask(id="task_001", title="Fix bug")
        d = t.to_dict()
        assert d["id"] == "task_001"
        assert d["title"] == "Fix bug"


# ── TaskStore ─────────────────────────────────────────────────────────

class TestTaskStore:
    def test_empty_store(self, tmp_path):
        store = TaskStore(tmp_path / "tasks")
        assert store.load_all() == []

    def test_add_and_load(self, tmp_path):
        store = TaskStore(tmp_path / "tasks")
        task = store.add(GameTask(title="Test task"))
        assert task.id.startswith("task_")
        assert task.created_at != ""

        all_tasks = store.load_all()
        assert len(all_tasks) == 1
        assert all_tasks[0].title == "Test task"

    def test_update(self, tmp_path):
        store = TaskStore(tmp_path / "tasks")
        task = store.add(GameTask(title="Original"))
        updated = store.update(task.id, title="Updated", status="done")
        assert updated is not None
        assert updated.title == "Updated"
        assert updated.status == "done"

    def test_update_nonexistent(self, tmp_path):
        store = TaskStore(tmp_path / "tasks")
        assert store.update("nope", title="x") is None

    def test_delete(self, tmp_path):
        store = TaskStore(tmp_path / "tasks")
        task = store.add(GameTask(title="Delete me"))
        assert store.delete(task.id) is True
        assert store.load_all() == []

    def test_delete_nonexistent(self, tmp_path):
        store = TaskStore(tmp_path / "tasks")
        assert store.delete("nope") is False
