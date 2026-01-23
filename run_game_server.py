
import os
from gevent import monkey; monkey.patch_all()
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from socket_handler import sio, timer_background_task
from room_manager import room_manager
import socketio



def run():
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
        import models # Ensure tables are defined
        import controllers
        from py4web.core import bottle
    except Exception as e:
        print(f"CRITICAL: Failed to import controllers or py4web: {e}")
        import traceback
        traceback.print_exc()
        return

    # Mount bottle (py4web) app alongside SocketIO
    # bottle is a module, we need the WSGI app
    # Create a simple WSGI middleware to strip /react-py4web prefix
    wsgi_app = bottle.default_app()
    
    def prefix_middleware(environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/react-py4web'):
            environ['PATH_INFO'] = path[len('/react-py4web'):] or '/'
        return wsgi_app(environ, start_response)

    app = socketio.WSGIApp(sio, prefix_middleware)
    
    print("Starting Python Game Server on port 3005 (Gevent)...")
    print("Routes: SocketIO + Py4Web endpoints")
    
    sio.start_background_task(timer_background_task, room_manager)
    server = pywsgi.WSGIServer(('0.0.0.0', 3005), app, handler_class=WebSocketHandler)

    server.serve_forever()

if __name__ == '__main__':
    run()
