import os
from gevent import monkey; monkey.patch_all()
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from server.socket_handler import sio, timer_background_task
from server.room_manager import room_manager
import socketio



def run():
    # PATH FIX: Add current directory to sys.path explicitly to ensure 'server' package is found
    # This is redundand usually but good for safety
    import sys
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())

    # PATCH: py4web crashes on top-level modules because it expects apps.app_name.controllers
    # We monkeypatch it to handle this case, BEFORE importing controllers which triggers route registration.
    from py4web import core
    
    def safe_module2filename(module):
        try:
             # If it's a top-level module (no dots), just return the name
            if '.' not in module:
                return module + ".py"
            # Otherwise use original logic: os.path.join(*module.split(".")[1:])
            parts = module.split(".")[1:]
            if not parts:
                 return module + ".py"
            return os.path.join(*parts)
        except:
            return module
            
    # Apply Patch
    core.module2filename = safe_module2filename

    # Now we can safely import controllers
    try:
        import server.models # Ensure tables are defined
        import server.controllers # Register routes (Note: May fail to register without app.route)
        import server.academy_controllers # Register Academy routes
        import server.controllers_replay # Register Replay routes
        from py4web.core import bottle
        
    except Exception as e:
        with open("logs/routes_dump.txt", "a") as f:
            f.write(f"CRITICAL: Failed to import controllers or py4web: {e}\n")
            import traceback
            f.write(traceback.format_exc())
        return

    # Mount bottle (py4web) app alongside SocketIO
    # bottle is a module, we need the WSGI app
    wsgi_app = bottle.default_app()
    
    # FIX: Explicitly bind Replay routes to this app instance to avoid Split Brain
    server.controllers_replay.bind(wsgi_app)
    
    # FIX: Explicitly bind Main Controller routes + Static Files
    server.controllers.bind(wsgi_app)
    
    def prefix_middleware(environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/react-py4web'):
            environ['PATH_INFO'] = path[len('/react-py4web'):] or '/'
        return wsgi_app(environ, start_response)

    ws_app = socketio.WSGIApp(sio, prefix_middleware)
    
    with open("logs/import_debug.txt", "a") as f:
        f.write(f"DEBUG: Main.py App ID: {id(bottle.default_app())}\n")
    
    print("Starting Python Game Server on port 3005 (Gevent)...")
    print("Routes: SocketIO + Py4Web endpoints")
    with open("logs/routes_dump.txt", "a") as f:
        f.write("----- REGISTERED ROUTES -----\n")
        f.write("----- REGISTERED ROUTES (Logging disabled to prevent crash) -----\n")
    
    sio.start_background_task(timer_background_task, room_manager)
    server = pywsgi.WSGIServer(('0.0.0.0', 3005), ws_app, handler_class=WebSocketHandler)

    with open("logs/routes_dump.txt", "a") as f:
        f.write("DEBUG: SERVER READY. Entering serve_forever()...\n")

    try:
        server.serve_forever()
    except Exception as e:
        import traceback
        with open("logs/crash.log", "a") as f:
             f.write(f"CRITICAL CRASH in serve_forever: {e}\n")
             f.write(traceback.format_exc())
        print(f"CRITICAL CRASH: {e}")
        raise

if __name__ == '__main__':
    run()
