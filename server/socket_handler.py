"""
Socket.IO event handler facade.

This module creates the sio instance and registers all handlers from sub-modules.
It re-exports key symbols for backward compatibility with application.py and bot_orchestrator.py.
"""
import socketio
import logging

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/server_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import Orchestrator
import server.bot_orchestrator as bot_orchestrator

print(f"DEBUG: Loading socket_handler.py as {__name__} | ID: {id(bot_orchestrator)}")

# Create a Socket.IO server
sio = socketio.Server(async_mode='gevent', cors_allowed_origins='*')

# Shared state
connected_users = {}  # sid -> {user_id, email, username, ...}

# --- Register Handlers from Sub-Modules ---
from server.handlers import telemetry, room_lifecycle, game_actions

telemetry.register(sio)
room_lifecycle.register(sio, connected_users)
game_actions.register(sio)

# --- Re-exports for backward compatibility ---
# application.py imports: sio, timer_background_task
# bot_orchestrator.py imports: auto_restart_round
from server.handlers.timer import timer_background_task as _timer_bg

def timer_background_task(room_manager_instance):
    """Wrapper that passes sio to the handler module's implementation."""
    _timer_bg(sio, room_manager_instance)

from server.handlers.game_lifecycle import auto_restart_round as _auto_restart

def auto_restart_round(game, room_id):
    """Wrapper that passes sio to the handler module's implementation."""
    _auto_restart(sio, game, room_id)

# Legacy re-exports used by bot_orchestrator
from server.handlers.game_lifecycle import (
    broadcast_game_update as _broadcast,
    handle_bot_turn as _handle_bot,
    save_match_snapshot,
    handle_bot_speak as _handle_speak,
)

def broadcast_game_update(game, room_id):
    _broadcast(sio, game, room_id)

def handle_bot_turn(game, room_id):
    _handle_bot(sio, game, room_id)

def handle_bot_speak(game, room_id, player, action, result):
    _handle_speak(sio, game, room_id, player, action, result)
