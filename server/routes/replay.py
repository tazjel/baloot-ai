"""
Match history / replay routes.
"""
import json
from py4web import action, request, response
from server.common import db, logger
from server.room_manager import room_manager
from server.serializers import serialize


@action('match_history/<game_id>', method=['GET', 'OPTIONS'])
def get_match_history(game_id):
    """Fetch full match history for Time Travel replay."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

    if request.method == 'OPTIONS':
        return ""

    try:
        game = room_manager.get_game(game_id)
        if not game:
            record = db.match_archive(game_id=game_id)
            if record and record.history_json:
                try:
                    return {"history": json.loads(record.history_json)}
                except:
                    pass

            response.status = 404
            return {"error": "Game not found"}

        return {"history": serialize(game.full_match_history)}
    except Exception as e:
        logger.error(f"Error in get_match_history: {e}")
        import traceback
        traceback.print_exc()
        response.status = 500
        return {"error": f"Internal Error: {str(e)}"}


def bind_replay(safe_mount):
    """Bind replay routes to the app."""
    safe_mount('/match_history/<game_id>', 'GET', get_match_history)
    safe_mount('/match_history/<game_id>', 'OPTIONS', get_match_history)
