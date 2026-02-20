from __future__ import annotations
from py4web import request, response
from py4web.core import bottle

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://baloot-ai.web.app"
]

def configure_cors(app: bottle.Bottle) -> None:
    """
    Configures CORS for the given Bottle application.
    Adds 'after_request' hook to set CORS headers and handles OPTIONS requests.
    """
    @app.hook('after_request')
    def enable_cors():
        origin = request.headers.get('Origin')
        if origin in ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, Authorization'

    # Handle OPTIONS for all routes
    @app.route('/<:re:.*>', method='OPTIONS')
    def handle_options():
        return {}
