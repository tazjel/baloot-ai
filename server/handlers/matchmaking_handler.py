"""
server/handlers/matchmaking_handler.py — Socket.IO events for matchmaking.

Handles queue_join, queue_leave, and queue_status events.
Runs a background match sweep when players join.
"""
from __future__ import annotations

import logging

from server.matchmaking import matchmaking_queue, MatchResult
from server.room_manager import room_manager
from server.rate_limiter import limiter

logger = logging.getLogger(__name__)

# Default ELO for unranked / guest players
DEFAULT_ELO = 1000


def register(sio, connected_users):
    """Register matchmaking event handlers on the Socket.IO server."""

    def _create_match_room(sio, match: MatchResult, connected_users: dict):
        """Create a game room for a matched group and notify players."""
        room_id = room_manager.create_room()
        if not room_id:
            logger.error("Failed to create room for match")
            return

        game = room_manager.get_game(room_id)
        if not game:
            return

        # Add matched players to the game
        for i, entry in enumerate(match.players):
            player = game.add_player(entry.sid, entry.player_name)
            if player:
                player.is_bot = False
                # Track email for session recovery
                room_manager.track_player_email(entry.email, room_id, player.index)
                sio.enter_room(entry.sid, room_id)
                room_manager.track_player(entry.sid, room_id)

        # Start the game
        if len(game.players) == 4:
            from server.handlers.game_lifecycle import handle_bot_turn

            if game.start_game():
                room_manager.save_game(game)

                # Notify each player individually with their index
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
                    f"Match room {room_id} started with "
                    f"{[p.email for p in match.players]}"
                )
        else:
            room_manager.save_game(game)

    @sio.event
    def queue_join(sid, data):
        """Join the matchmaking queue.

        Expects: {playerName: str}
        Returns: {success: bool, position: int, queueSize: int}
        """
        if not isinstance(data, dict):
            return {"success": False, "error": "Invalid request format"}

        # Rate limit: 5 queue joins per minute
        if not limiter.check_limit(f"queue_join:{sid}", 5, 60):
            return {"success": False, "error": "Too many requests. Please wait."}

        player_name = data.get("playerName", "Guest")

        # Get ELO from authenticated user or use default
        email = "guest"
        elo = DEFAULT_ELO
        if sid in connected_users:
            user = connected_users[sid]
            email = user.get("email", "guest")
            # Try to get ELO from user data (set during connect if available)
            elo = user.get("elo", DEFAULT_ELO)

        success = matchmaking_queue.enqueue(
            email=email,
            player_name=player_name,
            elo=elo,
            sid=sid,
        )

        if not success:
            return {"success": False, "error": "Already in queue"}

        # Try to form matches immediately
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
        # Find player email from connected_users
        email = "guest"
        if sid in connected_users:
            email = connected_users[sid].get("email", "guest")

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
