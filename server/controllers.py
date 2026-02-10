"""
HTTP controllers facade.

This module re-exports all route handlers from server/routes/* sub-modules
and provides the bind(app) function for explicit route registration.
"""
import os
import logging

logger = logging.getLogger(__name__)

# --- Re-export all endpoint functions for backward compatibility ---
from server.routes.auth import user, signup, signin, token_required
from server.routes.game import save_score, leaderboard, health_check, catch_all_v2
from server.routes.brain import (
    get_training_data, submit_training,
    get_brain_memory, delete_brain_memory
)
from server.routes.puzzles import get_puzzles, get_puzzle_detail
from server.routes.qayd import confirm_qayd, handle_qayd_trigger, update_director_config


# --- Explicit Binding for Custom Runner ---
from py4web.core import bottle


def bind(app):
    """
    Explicitly bind all controller actions to the main Bottle app instance.
    This bypasses py4web's auto-discovery which fails in this custom environment.
    """
    logger.debug(f"DEBUG: Binding Main Controllers to App {id(app)}")

    # Idempotency Guard
    if getattr(app, '_main_controllers_bound', False):
        logger.debug("DEBUG: Main Controllers already bound. Skipping.")
        return

    def safe_mount(path, method, callback):
        try:
            app.route(path, method=method, callback=callback)
            logger.debug(f"DEBUG: Mounted {path} [{method}]")
        except Exception as e:
            if "already registered" in str(e):
                logger.debug(f"DEBUG: Skipped duplicate mount {path}: {e}")
            else:
                logger.error(f"DEBUG: Failed to mount {path}: {e}")

    # 1. Static Files
    SERVER_FOLDER = os.path.dirname(__file__)
    PROJECT_ROOT = os.path.dirname(SERVER_FOLDER)
    STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'static')

    logger.debug(f"DEBUG: Serving Static from {STATIC_FOLDER} (Exists? {os.path.exists(STATIC_FOLDER)})")

    def serve_static(filepath):
        return bottle.static_file(filepath, root=STATIC_FOLDER)

    safe_mount('/static/<filepath:path>', 'GET', serve_static)

    # 2. Delegate to sub-module bind functions
    from server.routes.auth import bind_auth
    from server.routes.game import bind_game
    from server.routes.brain import bind_brain
    from server.routes.puzzles import bind_puzzles
    from server.routes.qayd import bind_qayd

    bind_auth(safe_mount)
    bind_brain(safe_mount)
    bind_puzzles(safe_mount)
    bind_qayd(safe_mount)
    bind_game(safe_mount)  # Must be last (catch-all route)

    setattr(app, '_main_controllers_bound', True)
