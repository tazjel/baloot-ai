import os
import sys

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gevent import monkey; monkey.patch_all()
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from server.application import create_app

def run():
    print("Starting Python Game Server on port 3005 (Gevent)...")
    
    try:
        app = create_app()
        server = pywsgi.WSGIServer(('0.0.0.0', 3005), app, handler_class=WebSocketHandler)
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
