"""
Room lifecycle handlers: connect, disconnect, create_room, join_room, add_bot, check_start.
"""
import html
import re
import time
import logging

from server.room_manager import room_manager
from ai_worker.personality import PROFILES, BALANCED, AGGRESSIVE, CONSERVATIVE
from server.rate_limiter import limiter
import server.auth_utils as auth_utils

logger = logging.getLogger(__name__)

# --- Input Sanitization ---
MAX_ROOM_ID_LEN = 64
MAX_PLAYER_NAME_LEN = 32
_CONTROL_CHARS = re.compile(r'[\x00-\x1f\x7f-\x9f]')


def _sanitize_player_name(raw: str) -> str:
    """Sanitize player name: strip control chars, HTML-escape, limit length."""
    if not isinstance(raw, str) or not raw.strip():
        return 'Guest'
    name = _CONTROL_CHARS.sub('', raw)        # remove control characters
    name = html.escape(name.strip())          # escape HTML entities
    name = name[:MAX_PLAYER_NAME_LEN]         # enforce length limit
    return name if name else 'Guest'


def _validate_room_id(room_id) -> bool:
    """Validate room ID format: non-empty string within length limit."""
    return isinstance(room_id, str) and 0 < len(room_id) <= MAX_ROOM_ID_LEN


def register(sio, connected_users):
    """Register room lifecycle event handlers on the given sio instance."""

    @sio.event
    def connect(sid, environ, auth=None):
        # Support both auth dict and query params (for some clients)
        token = (auth or {}).get('token')

        # Also check query string as fallback
        if not token:
            from urllib.parse import parse_qs
            qs = environ.get('QUERY_STRING', '')
            params = parse_qs(qs)
            if 'token' in params:
                token = params['token'][0]

        if not token:
            logger.info(f"Client connected (Guest): {sid}")
            return True  # Accepted as Guest

        user_data = auth_utils.verify_token(token)
        if not user_data:
            logger.warning(f"Invalid Token for SID: {sid}")
            return False  # Reject connection

        # Success! Store in memory for instant access
        connected_users[sid] = user_data
        logger.info(f"Authorized {user_data.get('email')} (SID: {sid})")
        return True

    @sio.event
    def disconnect(sid):
        logger.info(f"Client disconnected: {sid}")
        # Cleanup auth memory
        if sid in connected_users:
            del connected_users[sid]
        # Cleanup player-to-room tracking
        room_manager.untrack_player(sid)

    @sio.event
    def create_room(sid, data):
        logger.info(f"create_room called by {sid}")

        # Rate Limit: 5 per minute per SID (or IP if available)
        if not limiter.check_limit(f"create_room:{sid}", 5, 60):
            return {'success': False, 'error': 'Rate limit exceeded. Please wait.'}

        room_id = room_manager.create_room()
        if not room_id:
            return {'success': False, 'error': 'Server at capacity. Please try again later.'}
        return {'success': True, 'roomId': room_id}

    @sio.event
    def join_room(sid, data):
        if not isinstance(data, dict):
            return {'success': False, 'error': 'Invalid request format'}

        # Rate Limit: 10 per minute per SID
        if not limiter.check_limit(f"join_room:{sid}", 10, 60):
            return {'success': False, 'error': 'Too many join attempts. Please wait.'}

        from server.handlers.game_lifecycle import handle_bot_turn

        room_id = data.get('roomId')
        if not _validate_room_id(room_id):
            return {'success': False, 'error': 'Invalid roomId'}

        player_name = _sanitize_player_name(data.get('playerName', 'Guest'))

        game = room_manager.get_game(room_id)
        if not game:
            return {'success': False, 'error': 'Room not found'}

        # Duplicate-join guard: if SID is already in game, return existing state
        existing = next((p for p in game.players if p.id == sid), None)
        if existing:
            sio.enter_room(sid, room_id)
            return {
                'success': True,
                'gameState': game.get_game_state(),
                'yourIndex': existing.index
            }

        # RESERVED SEAT LOGIC (For Replay Forks)
        reserved = next((p for p in game.players if p.id == "RESERVED_FOR_USER"), None)
        if reserved:
            logger.info(f"User {sid} claiming RESERVED seat in room {room_id}")
            reserved.id = sid
            reserved.name = player_name
            player = reserved
        else:
            player = game.add_player(sid, player_name)

        if not player:
            return {'success': False, 'error': 'Room full'}

        # CRITICAL FIX: If a human joins, ensure they are NOT marked as a bot
        if player.is_bot:
            logger.warning(f"User {sid} reclaiming Bot Seat {player.index} ({player.name})")
            player.is_bot = False
            player.id = sid
            room_manager.save_game(game)

        sio.enter_room(sid, room_id)
        room_manager.track_player(sid, room_id)

        # For testing: Auto-add 3 bots when first player joins
        if len(game.players) == 1:
            bot_personas = [BALANCED, AGGRESSIVE, CONSERVATIVE]
            # Read difficulty from join data (defaults to HARD)
            bot_difficulty = data.get('botDifficulty', 'HARD')

            for i, persona in enumerate(bot_personas):
                bot_id = f"BOT_{i}_{int(time.time()*1000)}"
                display_name = f"{persona.name} (Bot)"

                bot_player = game.add_player(bot_id, display_name, avatar=persona.avatar_id)
                if bot_player:
                    bot_player.is_bot = True
                    bot_player.profile = persona.name
                    bot_player.difficulty = bot_difficulty
                    sio.emit('player_joined', {'player': bot_player.to_dict()}, room=room_id)

        # Broadcast to room
        sio.emit('player_joined', {'player': player.to_dict()}, room=room_id, skip_sid=sid)

        if len(game.players) == 4:
            if game.start_game():
                sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                handle_bot_turn(sio, game, room_id)

        # SAVE GAME STATE (Persist Player Join)
        room_manager.save_game(game)

        response = {
            'success': True,
            'gameState': game.get_game_state(),
            'yourIndex': player.index
        }

        return response

    @sio.event
    def add_bot(sid, data):
        if not isinstance(data, dict):
            return {'success': False, 'error': 'Invalid request format'}

        # Rate Limit: 10 per minute per SID
        if not limiter.check_limit(f"add_bot:{sid}", 10, 60):
            return {'success': False, 'error': 'Too many requests. Please wait.'}

        from server.handlers.game_lifecycle import handle_bot_turn

        room_id = data.get('roomId')
        if not _validate_room_id(room_id):
            return {'success': False, 'error': 'Invalid roomId'}
        if room_id not in room_manager.games:
            return {'success': False, 'error': 'Room not found'}

        game = room_manager.games[room_id]

        # Cycle through personas: Balanced -> Aggressive -> Conservative
        personas = [BALANCED, AGGRESSIVE, CONSERVATIVE]
        persona = personas[len(game.players) % 3]

        name = f"{persona.name} (Bot)"
        bot_difficulty = data.get('difficulty', 'HARD')

        bot_id = f"BOT_{len(game.players)}_{int(time.time())}"
        player = game.add_player(bot_id, name, avatar=persona.avatar_id)

        if not player:
            return {'success': False, 'error': 'Room full'}

        player.is_bot = True
        player.profile = persona.name
        player.difficulty = bot_difficulty
        room_manager.save_game(game)

        sio.emit('player_joined', {'player': player.to_dict()}, room=room_id)

        if len(game.players) == 4:
            if game.start_game():
                sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                handle_bot_turn(sio, game, room_id)

        return {'success': True}

    @sio.event
    def check_start(sid, data):
        if not isinstance(data, dict):
            return {'success': False, 'error': 'Invalid request format'}

        from server.handlers.game_lifecycle import handle_bot_turn

        room_id = data.get('roomId')
        if not _validate_room_id(room_id):
            return {'success': False, 'error': 'Invalid roomId'}
        game = room_manager.get_game(room_id)
        if game and len(game.players) == 4:
            if game.start_game():
                room_manager.save_game(game)
                sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                handle_bot_turn(sio, game, room_id)
