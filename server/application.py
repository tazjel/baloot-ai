
import os
import sys
import logging
import traceback
import socketio
from py4web.core import bottle
from server.socket_handler import sio, timer_background_task
from server.room_manager import room_manager
from server.core_patch import apply_py4web_patches

logger = logging.getLogger(__name__)

def create_app():
    """
    Factory function to create and configure the WSGI application.
    """
    # 1. Path Safety
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())

    # 2. Apply Patches
    apply_py4web_patches()

    # 2.5 Clear Stale Games (Dev Mode)
    try:
        room_manager.clear_all_games()
    except Exception as e:
        logger.warning(f"Failed to clear games: {e}")

    # 3. Import Controllers (Register Routes)
    # Patches must be applied BEFORE imports
    try:
        import server.models # Ensure tables are defined
        import server.controllers
        
    except Exception as e:
        with open("logs/routes_dump.txt", "a") as f:
            f.write(f"CRITICAL: Failed to import controllers: {e}\n")
            f.write(traceback.format_exc())
        raise

    # 4. Create WSGI App
    wsgi_app = bottle.default_app()
    
    # 5. Explicit Binding (Idempotent)
    server.controllers.bind(wsgi_app)
    
    # 6. SocketIO Setup
    def prefix_middleware(environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/react-py4web'):
            environ['PATH_INFO'] = path[len('/react-py4web'):] or '/'
        return wsgi_app(environ, start_response)

    ws_app = socketio.WSGIApp(sio, prefix_middleware)
    
    # 7. Start Background Tasks
    sio.start_background_task(timer_background_task, room_manager)
    
    return ws_app
