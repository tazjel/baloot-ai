"""
server/matchmaking.py — Skill-based matchmaking queue for multiplayer.

Manages a queue of players waiting for a match, groups them by ELO proximity,
and creates game rooms when 4 compatible players are found.

Uses an in-memory queue with periodic matching sweeps. Redis is used only
for ELO lookups (via the existing elo_engine).
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────────

# Maximum ELO difference between players in a match
MAX_ELO_SPREAD = 300

# How much the spread widens per second of wait time (relaxation)
ELO_SPREAD_PER_SECOND = 5

# Maximum wait time before force-matching with anyone (seconds)
MAX_WAIT_SECONDS = 120

# Minimum players needed for a match
PLAYERS_PER_MATCH = 4


@dataclass
class QueueEntry:
    """A player waiting in the matchmaking queue."""

    email: str
    player_name: str
    elo: int
    enqueue_time: float = field(default_factory=time.time)
    sid: str = ""  # Socket.IO session ID

    @property
    def wait_seconds(self) -> float:
        """How long this player has been waiting."""
        return time.time() - self.enqueue_time

    @property
    def effective_spread(self) -> float:
        """ELO spread tolerance, widening over time."""
        base = MAX_ELO_SPREAD
        relaxation = self.wait_seconds * ELO_SPREAD_PER_SECOND
        return base + relaxation


@dataclass
class MatchResult:
    """A completed match assignment."""

    room_id: str
    players: list[QueueEntry]
    avg_elo: float
    timestamp: float = field(default_factory=time.time)


class MatchmakingQueue:
    """Thread-safe matchmaking queue with ELO-based skill matching.

    Players join the queue and are grouped into matches of 4 when
    their ELO ratings are within an acceptable spread. The spread
    widens over time so no one waits forever.
    """

    def __init__(self):
        self._queue: list[QueueEntry] = []
        self._lock = Lock()
        # Track queued emails to prevent duplicate joins
        self._queued_emails: set[str] = set()

    @property
    def queue_size(self) -> int:
        """Number of players currently in queue."""
        return len(self._queue)

    def enqueue(self, email: str, player_name: str, elo: int, sid: str = "") -> bool:
        """Add a player to the matchmaking queue.

        Returns True if successfully added, False if already in queue.
        """
        with self._lock:
            if email in self._queued_emails:
                logger.info(f"Player {email} already in queue, skipping")
                return False

            entry = QueueEntry(
                email=email,
                player_name=player_name,
                elo=elo,
                sid=sid,
            )
            self._queue.append(entry)
            self._queued_emails.add(email)
            logger.info(
                f"Player queued: {email} (ELO={elo}, queue_size={len(self._queue)})"
            )
            return True

    def dequeue(self, email: str) -> bool:
        """Remove a player from the queue (e.g., cancelled search).

        Returns True if the player was found and removed.
        """
        with self._lock:
            before = len(self._queue)
            self._queue = [e for e in self._queue if e.email != email]
            self._queued_emails.discard(email)
            removed = len(self._queue) < before
            if removed:
                logger.info(f"Player dequeued: {email}")
            return removed

    def is_queued(self, email: str) -> bool:
        """Check if a player is currently in the queue."""
        return email in self._queued_emails

    def try_match(self) -> list[MatchResult]:
        """Attempt to form matches from the current queue.

        Sorts players by ELO and greedily groups compatible players.
        Returns a list of MatchResult objects for any matches formed.
        """
        with self._lock:
            if len(self._queue) < PLAYERS_PER_MATCH:
                return []

            # Sort by ELO for greedy grouping
            self._queue.sort(key=lambda e: e.elo)

            matches: list[MatchResult] = []
            remaining: list[QueueEntry] = []
            i = 0

            while i <= len(self._queue) - PLAYERS_PER_MATCH:
                group = self._queue[i : i + PLAYERS_PER_MATCH]

                # Check if all players in the group are compatible
                if self._is_compatible_group(group):
                    room_id = str(uuid.uuid4())[:8]
                    avg_elo = sum(p.elo for p in group) / len(group)
                    match = MatchResult(
                        room_id=room_id,
                        players=group,
                        avg_elo=avg_elo,
                    )
                    matches.append(match)

                    # Remove matched players from tracking
                    for p in group:
                        self._queued_emails.discard(p.email)

                    logger.info(
                        f"Match formed: room={room_id}, "
                        f"players={[p.email for p in group]}, "
                        f"avg_elo={avg_elo:.0f}"
                    )
                    i += PLAYERS_PER_MATCH
                else:
                    # First player doesn't match — move to remaining
                    remaining.append(self._queue[i])
                    i += 1

            # Add any unmatched players back
            remaining.extend(self._queue[i:])
            self._queue = remaining

            return matches

    def _is_compatible_group(self, group: list[QueueEntry]) -> bool:
        """Check if a group of players can be matched together.

        All pairs must have ELO within each player's effective spread.
        """
        for a in group:
            for b in group:
                if a is b:
                    continue
                diff = abs(a.elo - b.elo)
                # Both players must accept the spread
                if diff > a.effective_spread or diff > b.effective_spread:
                    return False
        return True

    def cleanup_expired(self) -> list[QueueEntry]:
        """Remove players who have been waiting too long.

        Returns the list of expired entries (for notification).
        """
        with self._lock:
            now = time.time()
            expired = [
                e for e in self._queue
                if (now - e.enqueue_time) > MAX_WAIT_SECONDS * 2
            ]
            if expired:
                self._queue = [
                    e for e in self._queue
                    if (now - e.enqueue_time) <= MAX_WAIT_SECONDS * 2
                ]
                for e in expired:
                    self._queued_emails.discard(e.email)
                logger.info(f"Expired {len(expired)} queue entries")
            return expired

    def get_queue_status(self) -> dict:
        """Return queue statistics for monitoring."""
        with self._lock:
            if not self._queue:
                return {
                    "queue_size": 0,
                    "avg_wait": 0.0,
                    "elo_range": (0, 0),
                }
            wait_times = [e.wait_seconds for e in self._queue]
            elos = [e.elo for e in self._queue]
            return {
                "queue_size": len(self._queue),
                "avg_wait": sum(wait_times) / len(wait_times),
                "elo_range": (min(elos), max(elos)),
            }


# Global instance
matchmaking_queue = MatchmakingQueue()
