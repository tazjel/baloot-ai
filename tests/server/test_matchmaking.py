"""Tests for M-MP6: Matchmaking Queue — queue logic and match formation."""
from __future__ import annotations

import time
import unittest

from server.matchmaking import (
    MatchmakingQueue,
    QueueEntry,
    MAX_ELO_SPREAD,
    PLAYERS_PER_MATCH,
)


class TestQueueEntry(unittest.TestCase):
    """Test QueueEntry dataclass properties."""

    def test_wait_seconds_increases(self):
        entry = QueueEntry(email="a@test.com", player_name="A", elo=1000,
                           enqueue_time=time.time() - 10)
        self.assertGreaterEqual(entry.wait_seconds, 10)

    def test_effective_spread_grows_with_wait(self):
        entry = QueueEntry(email="a@test.com", player_name="A", elo=1000,
                           enqueue_time=time.time() - 30)
        # After 30 seconds, spread should be > MAX_ELO_SPREAD
        self.assertGreater(entry.effective_spread, MAX_ELO_SPREAD)

    def test_fresh_entry_has_base_spread(self):
        entry = QueueEntry(email="a@test.com", player_name="A", elo=1000)
        # Just created — spread should be close to base
        self.assertAlmostEqual(entry.effective_spread, MAX_ELO_SPREAD, delta=10)


class TestMatchmakingQueue(unittest.TestCase):
    """Test queue operations: enqueue, dequeue, matching."""

    def setUp(self):
        self.q = MatchmakingQueue()

    def test_enqueue_success(self):
        result = self.q.enqueue("a@test.com", "Alice", 1000)
        self.assertTrue(result)
        self.assertEqual(self.q.queue_size, 1)

    def test_enqueue_duplicate_rejected(self):
        self.q.enqueue("a@test.com", "Alice", 1000)
        result = self.q.enqueue("a@test.com", "Alice Again", 1000)
        self.assertFalse(result)
        self.assertEqual(self.q.queue_size, 1)

    def test_dequeue_success(self):
        self.q.enqueue("a@test.com", "Alice", 1000)
        result = self.q.dequeue("a@test.com")
        self.assertTrue(result)
        self.assertEqual(self.q.queue_size, 0)

    def test_dequeue_nonexistent(self):
        result = self.q.dequeue("nobody@test.com")
        self.assertFalse(result)

    def test_is_queued(self):
        self.q.enqueue("a@test.com", "Alice", 1000)
        self.assertTrue(self.q.is_queued("a@test.com"))
        self.assertFalse(self.q.is_queued("b@test.com"))

    def test_dequeue_clears_is_queued(self):
        self.q.enqueue("a@test.com", "Alice", 1000)
        self.q.dequeue("a@test.com")
        self.assertFalse(self.q.is_queued("a@test.com"))


class TestMatchFormation(unittest.TestCase):
    """Test try_match() for grouping players."""

    def setUp(self):
        self.q = MatchmakingQueue()

    def test_no_match_with_fewer_than_4(self):
        for i in range(3):
            self.q.enqueue(f"p{i}@test.com", f"Player{i}", 1000)
        matches = self.q.try_match()
        self.assertEqual(len(matches), 0)
        self.assertEqual(self.q.queue_size, 3)

    def test_match_4_similar_elo(self):
        for i in range(4):
            self.q.enqueue(f"p{i}@test.com", f"Player{i}", 1000 + i * 10)
        matches = self.q.try_match()
        self.assertEqual(len(matches), 1)
        self.assertEqual(len(matches[0].players), PLAYERS_PER_MATCH)
        self.assertEqual(self.q.queue_size, 0)

    def test_match_removes_from_queue(self):
        for i in range(4):
            self.q.enqueue(f"p{i}@test.com", f"Player{i}", 1000)
        self.q.try_match()
        # All 4 should be removed
        for i in range(4):
            self.assertFalse(self.q.is_queued(f"p{i}@test.com"))

    def test_no_match_huge_elo_gap(self):
        """Players with 1000 ELO gap shouldn't match immediately."""
        self.q.enqueue("low@test.com", "Low", 500, sid="s1")
        self.q.enqueue("low2@test.com", "Low2", 550, sid="s2")
        self.q.enqueue("high@test.com", "High", 1800, sid="s3")
        self.q.enqueue("high2@test.com", "High2", 1850, sid="s4")
        matches = self.q.try_match()
        self.assertEqual(len(matches), 0)

    def test_multiple_matches_from_8_players(self):
        for i in range(8):
            self.q.enqueue(f"p{i}@test.com", f"Player{i}", 1000 + i * 5)
        matches = self.q.try_match()
        self.assertEqual(len(matches), 2)
        self.assertEqual(self.q.queue_size, 0)

    def test_match_result_has_avg_elo(self):
        elos = [900, 1000, 1100, 1050]
        for i, elo in enumerate(elos):
            self.q.enqueue(f"p{i}@test.com", f"Player{i}", elo)
        matches = self.q.try_match()
        self.assertEqual(len(matches), 1)
        expected_avg = sum(elos) / len(elos)
        self.assertAlmostEqual(matches[0].avg_elo, expected_avg, places=0)

    def test_match_result_has_room_id(self):
        for i in range(4):
            self.q.enqueue(f"p{i}@test.com", f"Player{i}", 1000)
        matches = self.q.try_match()
        self.assertIsNotNone(matches[0].room_id)
        self.assertTrue(len(matches[0].room_id) > 0)

    def test_relaxed_matching_after_wait(self):
        """Players with large ELO gap match after waiting (spread widens)."""
        # Simulate entries that have been waiting 60 seconds
        now = time.time()
        with self.q._lock:
            for i, elo in enumerate([500, 700, 850, 1000]):
                entry = QueueEntry(
                    email=f"p{i}@test.com",
                    player_name=f"Player{i}",
                    elo=elo,
                    enqueue_time=now - 60,  # 60 seconds ago
                    sid=f"s{i}",
                )
                self.q._queue.append(entry)
                self.q._queued_emails.add(entry.email)

        matches = self.q.try_match()
        # After 60s, spread = 300 + 60*5 = 600, so 500 ELO gap should match
        self.assertEqual(len(matches), 1)


class TestQueueStatus(unittest.TestCase):
    """Test queue status reporting."""

    def setUp(self):
        self.q = MatchmakingQueue()

    def test_empty_queue_status(self):
        status = self.q.get_queue_status()
        self.assertEqual(status["queue_size"], 0)
        self.assertEqual(status["avg_wait"], 0.0)

    def test_status_with_players(self):
        self.q.enqueue("a@test.com", "Alice", 1000)
        self.q.enqueue("b@test.com", "Bob", 1200)
        status = self.q.get_queue_status()
        self.assertEqual(status["queue_size"], 2)
        self.assertEqual(status["elo_range"], (1000, 1200))
        self.assertGreaterEqual(status["avg_wait"], 0)


class TestCleanupExpired(unittest.TestCase):
    """Test queue cleanup of stale entries."""

    def setUp(self):
        self.q = MatchmakingQueue()

    def test_no_cleanup_for_fresh_entries(self):
        self.q.enqueue("a@test.com", "Alice", 1000)
        expired = self.q.cleanup_expired()
        self.assertEqual(len(expired), 0)
        self.assertEqual(self.q.queue_size, 1)

    def test_cleanup_removes_old_entries(self):
        """Entries older than MAX_WAIT_SECONDS * 2 are removed."""
        now = time.time()
        with self.q._lock:
            old_entry = QueueEntry(
                email="old@test.com",
                player_name="Old",
                elo=1000,
                enqueue_time=now - 300,  # 5 min ago (> 120*2=240 limit)
            )
            self.q._queue.append(old_entry)
            self.q._queued_emails.add("old@test.com")

        expired = self.q.cleanup_expired()
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0].email, "old@test.com")
        self.assertEqual(self.q.queue_size, 0)
        self.assertFalse(self.q.is_queued("old@test.com"))


if __name__ == "__main__":
    unittest.main()
