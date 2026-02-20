"""
CORS configuration for the Baloot AI server.

Centralizes allowed origins and provides a configure_cors() helper
for both Bottle (HTTP) and Socket.IO (WebSocket) layers.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Allowed origins — override via CORS_ORIGINS env var (comma-separated).
ALLOWED_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://baloot-ai.web.app",
]

_env_origins = os.environ.get("CORS_ORIGINS")
if _env_origins and _env_origins != "*":
    ALLOWED_ORIGINS = [o.strip() for o in _env_origins.split(",") if o.strip()]
    logger.info(f"CORS origins from env: {ALLOWED_ORIGINS}")


def is_origin_allowed(origin: str | None) -> bool:
    """Check if a request origin is in the allowed list."""
    if not origin:
        return False
    # Allow wildcard in dev mode
    if os.environ.get("CORS_ORIGINS") == "*":
        return True
    return origin in ALLOWED_ORIGINS


def configure_cors(app) -> None:
    """
    Add CORS headers to every response via a Bottle after_request hook.

    Usage::

        from server.cors_config import configure_cors
        configure_cors(bottle_app)
    """

    def _add_cors_headers():
        """Bottle after_request hook — runs after every request."""
        from py4web.core import bottle

        origin = bottle.request.headers.get("Origin", "")

        if is_origin_allowed(origin):
            bottle.response.headers["Access-Control-Allow-Origin"] = origin
        elif os.environ.get("CORS_ORIGINS") == "*":
            bottle.response.headers["Access-Control-Allow-Origin"] = "*"

        bottle.response.headers["Access-Control-Allow-Credentials"] = "true"
        bottle.response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        bottle.response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization"
        )

    app.add_hook("after_request", _add_cors_headers)
    logger.info(f"CORS configured — allowed origins: {ALLOWED_ORIGINS}")


def get_socketio_cors() -> list[str] | str:
    """Return CORS origins suitable for socketio.Server(cors_allowed_origins=...)."""
    if os.environ.get("CORS_ORIGINS") == "*":
        return "*"
    return ALLOWED_ORIGINS
