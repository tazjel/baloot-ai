"""
Socket.IO event handler setup.

Creates the sio instance and registers all handlers from sub-modules.
Re-exports sio and timer_background_task for application.py.
"""
import socketio
import logging

logger = logging.getLogger(__name__)

# Import Orchestrator
import server.bot_orchestrator as bot_orchestrator

logger.debug(f"Loading socket_handler.py as {__name__} | ID: {id(bot_orchestrator)}")

# Create a Socket.IO server
sio = socketio.Server(async_mode='gevent', cors_allowed_origins='*')

# Shared state
connected_users = {}  # sid -> {user_id, email, username, ...}

# --- Register Handlers from Sub-Modules ---
from server.handlers import telemetry, room_lifecycle, game_actions

telemetry.register(sio)
room_lifecycle.register(sio, connected_users)
game_actions.register(sio)

# --- Minimal re-exports for application.py ---
from server.handlers.timer import timer_background_task as _timer_bg

def timer_background_task(room_manager_instance):
    """Wrapper that passes sio to the handler module's implementation."""
    _timer_bg(sio, room_manager_instance)
