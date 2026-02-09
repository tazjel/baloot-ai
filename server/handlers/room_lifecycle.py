"""
Room lifecycle handlers: connect, disconnect, create_room, join_room, add_bot, check_start.
"""
import time
import logging

from server.room_manager import room_manager
from ai_worker.personality import PROFILES, BALANCED, AGGRESSIVE, CONSERVATIVE
from server.rate_limiter import limiter
import server.auth_utils as auth_utils

logger = logging.getLogger(__name__)


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
            print(f"Client connected (Guest): {sid}")
            return True  # Accepted as Guest

        user_data = auth_utils.verify_token(token)
        if not user_data:
            print(f"Invalid Token for SID: {sid}")
            return False  # Reject connection

        # Success! Store in memory for instant access
        connected_users[sid] = user_data
        print(f"Authorized {user_data.get('email')} (SID: {sid})")
        return True

    @sio.event
    def disconnect(sid):
        print(f"Client disconnected: {sid}")
        # Cleanup auth memory
        if sid in connected_users:
            del connected_users[sid]

    @sio.event
    def create_room(sid, data):
        print(f"create_room called by {sid}")

        # Rate Limit: 5 per minute per SID (or IP if available)
        if not limiter.check_limit(f"create_room:{sid}", 5, 60):
            return {'success': False, 'error': 'Rate limit exceeded. Please wait.'}

        room_id = room_manager.create_room()
        return {'success': True, 'roomId': room_id}

    @sio.event
    def join_room(sid, data):
        from server.handlers.game_lifecycle import handle_bot_turn
        
        room_id = data.get('roomId')
        player_name = data.get('playerName', 'Guest')

        game = room_manager.get_game(room_id)
        if not game:
            return {'success': False, 'error': 'Room not found'}

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

        # For testing: Auto-add 3 bots when first player joins
        if len(game.players) == 1:
            bot_personas = [BALANCED, AGGRESSIVE, CONSERVATIVE]

            for i, persona in enumerate(bot_personas):
                bot_id = f"BOT_{i}_{int(time.time()*1000)}"
                display_name = f"{persona.name} (Bot)"

                bot_player = game.add_player(bot_id, display_name, avatar=persona.avatar_id)
                if bot_player:
                    bot_player.is_bot = True
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
        from server.handlers.game_lifecycle import handle_bot_turn
        
        room_id = data.get('roomId')
        if not room_id or room_id not in room_manager.games:
            return {'success': False, 'error': 'Room not found'}

        game = room_manager.games[room_id]

        # Cycle through personas: Balanced -> Aggressive -> Conservative
        personas = [BALANCED, AGGRESSIVE, CONSERVATIVE]
        persona = personas[len(game.players) % 3]

        name = f"{persona.name} (Bot)"

        bot_id = f"BOT_{len(game.players)}_{int(time.time())}"
        player = game.add_player(bot_id, name, avatar=persona.avatar_id)

        if not player:
            return {'success': False, 'error': 'Room full'}

        player.is_bot = True
        room_manager.save_game(game)

        sio.emit('player_joined', {'player': player.to_dict()}, room=room_id)

        if len(game.players) == 4:
            if game.start_game():
                sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                handle_bot_turn(sio, game, room_id)

        return {'success': True}

    @sio.event
    def check_start(sid, data):
        from server.handlers.game_lifecycle import handle_bot_turn
        
        room_id = data.get('roomId')
        game = room_manager.get_game(room_id)
        if game and len(game.players) == 4:
            if game.start_game():
                room_manager.save_game(game)
                sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                handle_bot_turn(sio, game, room_id)
