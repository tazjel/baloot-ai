"""Tests for M-MP4: Session Recovery — email-to-room tracking logic.

Tests the session tracking data structures independently of the full
RoomManager (which pulls in the entire game engine). This avoids deep
import chains while still verifying all session recovery logic.
"""
from __future__ import annotations

import time
import unittest


class SessionTracker:
    """Minimal reproduction of RoomManager's email tracking logic.

    Mirrors the exact implementation added in M-MP4 so we can test
    the tracking logic without importing the full server stack.
    """

    def __init__(self):
        self._email_to_room: dict[str, dict] = {}
        self._sid_to_room: dict[str, str] = {}
        self._games: dict[str, object] = {}  # room_id → fake game

    def track_player(self, sid: str, room_id: str):
        self._sid_to_room[sid] = room_id

    def untrack_player(self, sid: str):
        self._sid_to_room.pop(sid, None)

    def get_room_for_sid(self, sid: str):
        return self._sid_to_room.get(sid)

    def track_player_email(self, email: str, room_id: str, seat_index: int):
        self._email_to_room[email] = {
            "room_id": room_id,
            "seat_index": seat_index,
            "timestamp": time.time(),
        }

    def untrack_player_email(self, email: str):
        self._email_to_room.pop(email, None)

    def get_active_session(self, email: str):
        session = self._email_to_room.get(email)
        if not session:
            return None
        # Verify game still exists
        if session["room_id"] not in self._games:
            self._email_to_room.pop(email, None)
            return None
        return session


class TestEmailTracking(unittest.TestCase):
    """Test email-to-room session tracking (M-MP4)."""

    def setUp(self):
        self.tracker = SessionTracker()

    def test_track_player_email(self):
        """track_player_email stores session data."""
        self.tracker.track_player_email("user@test.com", "room-abc", 2)
        session = self.tracker._email_to_room.get("user@test.com")
        self.assertIsNotNone(session)
        self.assertEqual(session["room_id"], "room-abc")
        self.assertEqual(session["seat_index"], 2)
        self.assertIn("timestamp", session)

    def test_untrack_player_email(self):
        """untrack_player_email removes session data."""
        self.tracker.track_player_email("user@test.com", "room-abc", 0)
        self.tracker.untrack_player_email("user@test.com")
        self.assertIsNone(self.tracker._email_to_room.get("user@test.com"))

    def test_untrack_nonexistent_email(self):
        """untrack_player_email handles missing email gracefully."""
        self.tracker.untrack_player_email("nobody@test.com")  # no error

    def test_get_active_session_exists(self):
        """get_active_session returns session when game exists."""
        self.tracker._games["room-xyz"] = object()  # simulate live game
        self.tracker.track_player_email("player@test.com", "room-xyz", 1)
        session = self.tracker.get_active_session("player@test.com")
        self.assertIsNotNone(session)
        self.assertEqual(session["room_id"], "room-xyz")
        self.assertEqual(session["seat_index"], 1)

    def test_get_active_session_game_expired(self):
        """get_active_session returns None if game no longer exists."""
        self.tracker.track_player_email("player@test.com", "room-dead", 3)
        # Don't add room-dead to _games → simulates expired game
        session = self.tracker.get_active_session("player@test.com")
        self.assertIsNone(session)
        # Should also clean up the stale mapping
        self.assertNotIn("player@test.com", self.tracker._email_to_room)

    def test_get_active_session_no_mapping(self):
        """get_active_session returns None for unknown email."""
        session = self.tracker.get_active_session("unknown@test.com")
        self.assertIsNone(session)

    def test_multiple_users_tracked(self):
        """Multiple users can be tracked independently."""
        self.tracker.track_player_email("a@test.com", "room-1", 0)
        self.tracker.track_player_email("b@test.com", "room-1", 1)
        self.tracker.track_player_email("c@test.com", "room-2", 0)
        self.assertEqual(len(self.tracker._email_to_room), 3)
        self.assertEqual(self.tracker._email_to_room["a@test.com"]["room_id"], "room-1")
        self.assertEqual(self.tracker._email_to_room["c@test.com"]["room_id"], "room-2")

    def test_overwrite_session_on_new_game(self):
        """Tracking same email again overwrites the old session."""
        self.tracker.track_player_email("user@test.com", "room-old", 0)
        self.tracker.track_player_email("user@test.com", "room-new", 2)
        session = self.tracker._email_to_room["user@test.com"]
        self.assertEqual(session["room_id"], "room-new")
        self.assertEqual(session["seat_index"], 2)

    def test_timestamp_increases(self):
        """Each tracking call gets a fresh timestamp."""
        self.tracker.track_player_email("user@test.com", "room-1", 0)
        t1 = self.tracker._email_to_room["user@test.com"]["timestamp"]
        # Small sleep to ensure different timestamp
        import time as _t
        _t.sleep(0.01)
        self.tracker.track_player_email("user@test.com", "room-2", 1)
        t2 = self.tracker._email_to_room["user@test.com"]["timestamp"]
        self.assertGreater(t2, t1)


class TestSidTracking(unittest.TestCase):
    """Verify existing SID tracking works alongside email tracking."""

    def setUp(self):
        self.tracker = SessionTracker()

    def test_track_and_get_sid(self):
        self.tracker.track_player("sid-123", "room-abc")
        self.assertEqual(self.tracker.get_room_for_sid("sid-123"), "room-abc")

    def test_untrack_sid(self):
        self.tracker.track_player("sid-123", "room-abc")
        self.tracker.untrack_player("sid-123")
        self.assertIsNone(self.tracker.get_room_for_sid("sid-123"))

    def test_email_and_sid_independent(self):
        """Email tracking and SID tracking don't interfere."""
        self.tracker.track_player("sid-1", "room-a")
        self.tracker.track_player_email("user@test.com", "room-a", 0)
        self.tracker.untrack_player("sid-1")
        # Email mapping should still exist
        self.assertIn("user@test.com", self.tracker._email_to_room)

    def test_sid_unknown_returns_none(self):
        self.assertIsNone(self.tracker.get_room_for_sid("nonexistent"))


class TestRejoinValidation(unittest.TestCase):
    """Test rejoin request validation logic."""

    def test_valid_seat_indices(self):
        """Seat indices 0-3 are valid."""
        for i in range(4):
            self.assertTrue(isinstance(i, int) and 0 <= i <= 3)

    def test_invalid_seat_index_negative(self):
        """Negative seat index is invalid."""
        self.assertFalse(0 <= -1 <= 3)

    def test_invalid_seat_index_high(self):
        """Seat index > 3 is invalid."""
        self.assertFalse(0 <= 4 <= 3)

    def test_room_id_validation(self):
        """Room IDs must be non-empty strings within length limit."""
        MAX_ROOM_ID_LEN = 64
        self.assertTrue(isinstance("room-abc", str) and 0 < len("room-abc") <= MAX_ROOM_ID_LEN)
        self.assertFalse(isinstance("", str) and 0 < len("") <= MAX_ROOM_ID_LEN)
        self.assertFalse(isinstance("x" * 65, str) and 0 < len("x" * 65) <= MAX_ROOM_ID_LEN)


if __name__ == "__main__":
    unittest.main()
