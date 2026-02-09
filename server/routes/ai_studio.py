"""
AI Studio routes: screenshot analysis, strategy advice, scenario generation, match analysis,
AI thoughts, mind map inference.
"""
import os
import mimetypes
import uuid
import logging
from py4web import action, request, response
from server.common import db, logger, redis_client
from ai_worker.llm_client import GeminiClient
from server.room_manager import room_manager
from server.serializers import serialize


@action('analyze_screenshot', method=['POST', 'OPTIONS'])
def analyze_screenshot():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    from server.settings import UPLOAD_FOLDER
    dataset_dir = os.path.join(UPLOAD_FOLDER, 'dataset')
    os.makedirs(dataset_dir, exist_ok=True)

    if request.method == 'OPTIONS':
        return ""

    if not request.files.get('screenshot'):
        response.status = 400
        return {"error": "No screenshot file provided"}

    f = request.files['screenshot']
    image_data = f.file.read()

    ext = mimetypes.guess_extension(f.content_type) or ".jpg"
    filename = f"img_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(dataset_dir, filename)

    with open(filepath, 'wb') as saved_file:
        saved_file.write(image_data)

    logger.debug(f"[DEBUG] Saved dataset image to {filepath}")
    logger.debug(f"[DEBUG] Analyzing screenshot. Size: {len(image_data)} bytes. Content-Type: {f.content_type}")

    debug_log_path = os.path.join("logs", "gemini_debug.log")
    with open(debug_log_path, "a") as logutils:
        logutils.write(f"\n[REQ] Analyze Screenshot. Size: {len(image_data)}\n")
        logutils.write(f"[REQ] API Key Present: {bool(os.environ.get('GEMINI_API_KEY'))}\n")

    try:
        gemini = GeminiClient()
        mime = f.content_type if f.content_type else 'image/jpeg'

        result = None
        if mime.startswith('video/'):
            result = gemini.analyze_video(filepath, mime_type=mime)
        else:
            result = gemini.analyze_image(image_data, mime_type=mime)

        if result:
            return {"data": result, "imageFilename": filename}
        else:
            response.status = 500
            return {"error": "Gemini returned empty result (check logs)"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        response.status = 500
        return {"error": f"Internal Error: {str(e)}"}


@action('ask_strategy', method=['POST', 'OPTIONS'])
def ask_strategy():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    game_state = data.get('gameState')

    if not game_state:
        response.status = 400
        return {"error": "Missing gameState"}

    bid = game_state.get('bid', {})
    mode = bid.get('type', 'SUN')
    trump = bid.get('suit')

    players = game_state.get('players', [])
    me = next((p for p in players if p['name'] == 'Me' or p['position'] == 'Bottom'), None)

    hand_strs = []
    if me:
        hand_strs = [f"{c['rank']}{c['suit']}" for c in me.get('hand', [])]

    played_map = game_state.get('playedCards', {})
    table_strs = [f"{c['rank']}{c['suit']}" for c in played_map.values()]

    context = {
        'mode': mode, 'trump': trump, 'hand': hand_strs,
        'table': table_strs, 'played_cards': [], 'position': 'Bottom'
    }

    # RAG Lite: Retrieve Relevant Examples
    examples = []
    try:
        rows = db(db.bot_training_data).select(orderby=~db.bot_training_data.created_on, limitby=(0, 20))
        for r in rows:
            try:
                example_state = r.game_state_json
                if mode and mode in example_state:
                    examples.append({
                        "state": example_state,
                        "correct_move": r.correct_move_json,
                        "reason": r.reason
                    })
            except:
                continue
            if len(examples) >= 3:
                break
    except Exception as e:
        logger.error(f"Failed to retrieve training examples: {e}")

    try:
        gemini = GeminiClient()
        result = gemini.analyze_hand(context, examples=examples)
        if result:
            return {"recommendation": result}
        else:
            return {"error": "AI could not determine a move."}
    except Exception as e:
        return {"error": str(e)}


@action('generate_scenario', method=['POST', 'OPTIONS'])
def generate_scenario():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    text = data.get('text')

    try:
        gemini = GeminiClient()
        result = gemini.generate_scenario_from_text(text)
        return {"data": result}
    except Exception as e:
        return {"error": str(e)}


@action('analyze_match', method=['POST', 'OPTIONS'])
def analyze_match():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    game_id = data.get('gameId')

    try:
        game = room_manager.get_game(game_id)
        if not game:
            return {"error": "Game not found in memory"}

        history = game.full_match_history

        gemini = GeminiClient()
        result = gemini.analyze_match_history(history)
        return {"analysis": result}
    except Exception as e:
        return {"error": str(e)}


@action('ai_thoughts/<game_id>', method=['GET', 'OPTIONS'])
def get_ai_thoughts(game_id):
    """Fetch live AI thoughts for a running game."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        if not redis_client:
            return {"thoughts": {}}

        import json
        pattern = f"bot:thought:{game_id}:*"
        keys = redis_client.keys(pattern)

        thoughts = {}
        if keys:
            values = redis_client.mget(keys)
            for k, v in zip(keys, values):
                try:
                    idx = int(k.split(':')[-1])
                    if v:
                        thoughts[idx] = json.loads(v)
                except:
                    pass

        return {"thoughts": serialize(thoughts)}

    except Exception as e:
        logger.error(f"Failed to fetch thoughts: {e}")
        return {"thoughts": {}}


@action('api/mind/inference/<game_id>', method=['GET', 'OPTIONS'])
def get_mind_inference(game_id):
    """Fetch 'Theory of Mind' probabilities for 3D visualization."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        if not redis_client:
            return {"mind_map": {}}

        import json
        pattern = f"bot:mind_map:{game_id}:*"
        keys = redis_client.keys(pattern)

        mind_map = {}
        if keys:
            values = redis_client.mget(keys)
            for k, v in zip(keys, values):
                try:
                    idx = int(k.split(':')[-1])
                    if v:
                        mind_map[idx] = json.loads(v)
                except:
                    pass

        return {"mind_map": mind_map}

    except Exception as e:
        logger.error(f"Failed to fetch mind map: {e}")
        return {"mind_map": {}}


def bind_ai_studio(safe_mount):
    """Bind AI studio routes to the app."""
    safe_mount('/analyze_screenshot', 'POST', analyze_screenshot)
    safe_mount('/analyze_screenshot', 'OPTIONS', analyze_screenshot)
    safe_mount('/ask_strategy', 'POST', ask_strategy)
    safe_mount('/ask_strategy', 'OPTIONS', ask_strategy)
    safe_mount('/generate_scenario', 'POST', generate_scenario)
    safe_mount('/generate_scenario', 'OPTIONS', generate_scenario)
    safe_mount('/analyze_match', 'POST', analyze_match)
    safe_mount('/analyze_match', 'OPTIONS', analyze_match)
    safe_mount('/ai_thoughts/<game_id>', 'GET', get_ai_thoughts)
    safe_mount('/ai_thoughts/<game_id>', 'OPTIONS', get_ai_thoughts)
    safe_mount('/api/mind/inference/<game_id>', 'GET', get_mind_inference)
    safe_mount('/api/mind/inference/<game_id>', 'OPTIONS', get_mind_inference)
