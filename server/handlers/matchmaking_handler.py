"""
server/handlers/matchmaking_handler.py — Socket.IO events for matchmaking.

Handles queue_join, queue_leave, and queue_status events.
Also starts a background matchmaking sweep that periodically checks
for enough players to form matches (fixes timing gaps between joins).
"""
from __future__ import annotations

import logging

from server.matchmaking import matchmaking_queue, matchmaking_sweep_task, MatchResult
from server.room_manager import room_manager
from server.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

# Default ELO for unranked / guest players
DEFAULT_ELO = 1000

# Module-level flag to prevent duplicate sweep tasks
_sweep_started = False


def _create_match_room(sio, match: MatchResult, connected_users: dict):
    """Create a game room for a matched group and notify players.

    Extracted to module level so it can be called from both the
    ``queue_join`` handler and the background sweep task.
    """
    room_id = room_manager.create_room()
    if not room_id:
        logger.error("Failed to create room for match")
        return

    game = room_manager.get_game(room_id)
    if not game:
        logger.error("Failed to get game for room %s", room_id)
        return

    # Add matched players to the game
    added = 0
    for i, entry in enumerate(match.players):
        player = game.add_player(entry.sid, entry.player_name)
        if player:
            player.is_bot = False
            room_manager.track_player_email(entry.email, room_id, player.index)
            sio.enter_room(entry.sid, room_id)
            room_manager.track_player(entry.sid, room_id)
            added += 1

    # Start the game once all 4 are seated
    if added == 4 and len(game.players) == 4:
        from server.handlers.game_lifecycle import handle_bot_turn

        if game.start_game():
            room_manager.save_game(game)

            for i, p in enumerate(game.players):
                sio.emit(
                    "match_found",
                    {
                        "roomId": room_id,
                        "yourIndex": p.index,
                        "gameState": game.get_game_state(),
                        "avgElo": match.avg_elo,
                    },
                    to=p.id,
                )

            logger.info(
                "Match room %s started with %s",
                room_id,
                [p.email for p in match.players],
            )
        else:
            logger.error("game.start_game() failed for room %s", room_id)
            room_manager.save_game(game)
    else:
        logger.warning(
            "Match room %s: only %d/4 players added, saving partial",
            room_id,
            added,
        )
        room_manager.save_game(game)


def register(sio, connected_users):
    """Register matchmaking event handlers on the Socket.IO server."""

    # --- Start background sweep (once per process) ---
    global _sweep_started
    if not _sweep_started:
        _sweep_started = True

        def _on_match_formed(match: MatchResult):
            _create_match_room(sio, match, connected_users)

        sio.start_background_task(matchmaking_sweep_task, sio, _on_match_formed)
        logger.info("Matchmaking background sweep task started")

    # Named rate limiter for matchmaking operations
    _mm_limiter = get_rate_limiter("matchmaking")

    @sio.event
    def queue_join(sid, data):
        """Join the matchmaking queue.

        Expects: {playerName: str}
        Returns: {success: bool, queueSize: int, avgWait: float}
        """
        if not isinstance(data, dict):
            return {"success": False, "error": "Invalid request format"}

        # Rate limit: 5 queue joins per minute per SID
        if not _mm_limiter.check_limit(f"queue_join:{sid}", 5, 60):
            logger.warning("Rate limited queue_join from sid=%s", sid)
            return {"success": False, "error": "Too many requests. Please wait."}

        player_name = data.get("playerName", "Guest")

        # Get ELO from authenticated user or use default
        elo = DEFAULT_ELO
        if sid in connected_users:
            user = connected_users[sid]
            email = user.get("email", f"guest_{sid}")
            elo = user.get("elo", DEFAULT_ELO)
        else:
            email = f"guest_{sid}"

        success = matchmaking_queue.enqueue(
            email=email,
            player_name=player_name,
            elo=elo,
            sid=sid,
        )

        if not success:
            return {"success": False, "error": "Already in queue"}

        # Try to form matches immediately (don't wait for sweep)
        matches = matchmaking_queue.try_match()
        for match in matches:
            _create_match_room(sio, match, connected_users)

        status = matchmaking_queue.get_queue_status()
        return {
            "success": True,
            "queueSize": status["queue_size"],
            "avgWait": status["avg_wait"],
        }

    @sio.event
    def queue_leave(sid, data):
        """Leave the matchmaking queue.

        Returns: {success: bool}
        """
        if sid in connected_users:
            email = connected_users[sid].get("email", f"guest_{sid}")
        else:
            email = f"guest_{sid}"

        removed = matchmaking_queue.dequeue(email)
        return {"success": removed}

    @sio.event
    def queue_status(sid, data):
        """Get current queue status.

        Returns: {queueSize: int, avgWait: float, eloRange: [int, int]}
        """
        status = matchmaking_queue.get_queue_status()
        return {
            "queueSize": status["queue_size"],
            "avgWait": round(status["avg_wait"], 1),
            "eloRange": list(status["elo_range"]),
        }
