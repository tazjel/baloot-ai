"""
Tests for capturer — event classification and GameCapturer properties.

Only tests pure functions (classify_event, classify_batch) and
non-browser GameCapturer state management. Does NOT test Playwright
browser integration.
"""
import pytest
from pathlib import Path

from gbaloot.core.capturer import (
    classify_event,
    classify_batch,
    GameCapturer,
)


# ── classify_event ────────────────────────────────────────────────────

class TestClassifyEvent:
    def test_bid_detected(self):
        msg = {"data": '"a_bid"'}
        assert classify_event(msg) is not None

    def test_card_played_detected(self):
        msg = {"data": '"a_card_played"'}
        assert classify_event(msg) is not None

    def test_cards_eating_detected(self):
        msg = {"data": '"a_cards_eating"'}
        assert classify_event(msg) is not None

    def test_game_state_detected(self):
        msg = {"data": '"game_state"'}
        assert classify_event(msg) is not None

    def test_non_game_message_returns_none(self):
        msg = {"data": "just some random text"}
        assert classify_event(msg) is None

    def test_empty_data_returns_none(self):
        msg = {"data": ""}
        assert classify_event(msg) is None

    def test_no_data_key(self):
        msg = {}
        assert classify_event(msg) is None

    def test_hokom_detected(self):
        msg = {"data": '"hokom"'}
        assert classify_event(msg) is not None

    def test_special_action_kaboot(self):
        msg = {"data": '"a_kaboot_call"'}
        assert classify_event(msg) is not None


# ── classify_batch ────────────────────────────────────────────────────

class TestClassifyBatch:
    def test_empty_batch(self):
        assert classify_batch([]) == []

    def test_mixed_batch(self):
        messages = [
            {"data": '"a_card_played"'},
            {"data": "hello"},
            {"data": '"a_bid"'},
        ]
        results = classify_batch(messages)
        assert len(results) == 3
        assert results[0][1] is not None   # card_played
        assert results[1][1] is None       # non-game
        assert results[2][1] is not None   # bid


# ── GameCapturer ──────────────────────────────────────────────────────

class TestGameCapturer:
    def test_initial_state(self, tmp_path):
        gc = GameCapturer(tmp_path / "captures")
        assert gc.message_count == 0
        assert gc.is_running is False
        assert gc.duration_sec == 0.0

    def test_output_dir_created(self, tmp_path):
        out = tmp_path / "test_captures"
        gc = GameCapturer(out)
        assert out.exists()

    def test_message_count_tracks_ws(self, tmp_path):
        gc = GameCapturer(tmp_path / "captures")
        gc.all_ws = [{"data": "msg1"}, {"data": "msg2"}]
        assert gc.message_count == 2

    def test_max_messages_constant(self, tmp_path):
        gc = GameCapturer(tmp_path / "captures")
        assert gc.MAX_MESSAGES == 50_000
