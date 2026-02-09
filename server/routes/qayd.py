"""
Qayd forensic challenge HTTP routes and Director/Commissioner config.
Deduplicated: handle_qayd_trigger and update_director_config were near-identical.
"""
import logging
from py4web import action, request, response
from server.common import logger
from server.room_manager import room_manager


@action('game/qayd/confirm', method=['POST', 'OPTIONS'])
def confirm_qayd():
    """User/Client confirmation of the Qayd verdict (Reviews Phase -> Resolved)."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    game_id = data.get('gameId')

    if not game_id:
        return {"error": "Missing gameId"}

    game = room_manager.get_game(game_id)
    if not game:
        return {"error": "Game not found"}

    if not hasattr(game, 'trick_manager'):
        return {"error": "Game engine not initialized"}

    result = game.trick_manager.confirm_qayd()
    return result


def _update_game_config(game_id, settings, bot_configs):
    """Shared implementation for qayd_trigger and director_update (were near-identical)."""
    game = room_manager.get_game(game_id)
    if not game:
        return 404, {"error": "Game not found"}

    logger.info(f"[DIRECTOR] Updating Game {game_id}")

    # 1. Update Global Settings
    if settings:
        logger.info(f"[DIRECTOR] Update Settings: {settings}")
        if hasattr(game, 'settings'):
            for k, v in settings.items():
                if hasattr(game.settings, k):
                    setattr(game.settings, k, v)
                elif isinstance(game.settings, dict):
                    game.settings[k] = v
        else:
            game.settings = settings

    # 2. Update Bot Configs
    if bot_configs:
        logger.info(f"[DIRECTOR] Update Bots: {bot_configs}")
        for idx_str, cfg in bot_configs.items():
            idx = int(idx_str)
            if 0 <= idx < len(game.players):
                p = game.players[idx]
                if 'strategy' in cfg:
                    p.strategy = cfg['strategy']
                if 'profile' in cfg:
                    p.profile = cfg['profile']

    return 200, {"success": True, "message": "Director Config Applied"}


@action('game/qayd/trigger', method=['POST', 'OPTIONS'])
def handle_qayd_trigger():
    """Updates game settings and player configs (Commissioner's Desk)."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    game_id = data.get('gameId')

    if not game_id:
        response.status = 400
        return {"error": "Missing gameId"}

    try:
        status, result = _update_game_config(
            game_id, data.get('settings'), data.get('botConfigs')
        )
        response.status = status
        return result
    except Exception as e:
        logger.error(f"Director Update Failed: {e}")
        import traceback
        traceback.print_exc()
        response.status = 500
        return {"error": str(e)}


@action('game/director/update', method=['POST', 'OPTIONS'])
def update_director_config():
    """Updates game settings and player configs (Commissioner's Desk)."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    game_id = data.get('gameId')

    if not game_id:
        response.status = 400
        return {"error": "Missing gameId"}

    try:
        status, result = _update_game_config(
            game_id, data.get('settings'), data.get('botConfigs')
        )
        response.status = status
        return result
    except Exception as e:
        logger.error(f"Director Update Failed: {e}")
        import traceback
        traceback.print_exc()
        response.status = 500
        return {"error": str(e)}


def bind_qayd(safe_mount):
    """Bind qayd and director routes to the app."""
    safe_mount('/game/qayd/trigger', 'POST', handle_qayd_trigger)
    safe_mount('/game/qayd/trigger', 'OPTIONS', handle_qayd_trigger)
    safe_mount('/game/director/update', 'POST', update_director_config)
    safe_mount('/game/director/update', 'OPTIONS', update_director_config)
