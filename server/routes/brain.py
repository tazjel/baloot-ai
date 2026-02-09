"""
Brain memory and training data routes.
"""
import json
from py4web import action, request, response
from server.common import db, logger, redis_client


@action('training_data', method=['GET', 'OPTIONS'])
@action.uses(db)
def get_training_data():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    rows = db(db.bot_training_data).select(orderby=~db.bot_training_data.created_on, limitby=(0, 50))
    return {"data": [r.as_dict() for r in rows]}


@action('submit_training', method=['POST', 'OPTIONS'])
@action.uses(db)
def submit_training():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    db.bot_training_data.insert(
        context_hash=data.get('contextHash'),
        game_state_json=data.get('gameState'),
        bad_move_json=data.get('badMove'),
        correct_move_json=data.get('correctMove'),
        reason=data.get('reason'),
        image_filename=data.get('imageFilename')
    )
    return {"message": "Training example saved"}


@action('brain/memory', method=['GET', 'OPTIONS'])
def get_brain_memory():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        if not redis_client:
            return {"memory": []}

        keys = redis_client.keys("brain:correct:*")

        memory = []
        if keys:
            pipe = redis_client.pipeline()
            for k in keys:
                pipe.get(k)
            values = pipe.execute()

            for k, v in zip(keys, values):
                if v:
                    try:
                        data = json.loads(v)
                        memory.append({
                            "hash": k.split(":")[-1],
                            "key": k,
                            "data": data
                        })
                    except:
                        pass

        return {"memory": memory}
    except Exception as e:
        print(f"Error fetching brain memory: {e}")
        return {"error": str(e)}


@action('brain/memory/<context_hash>', method=['DELETE', 'OPTIONS'])
def delete_brain_memory(context_hash):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        if not redis_client:
            return {"error": "Redis not connected"}

        key = f"brain:correct:{context_hash}"
        redis_client.delete(key)

        return {"success": True, "message": f"Deleted {key}"}
    except Exception as e:
        return {"error": str(e)}


def bind_brain(safe_mount):
    """Bind brain/training routes to the app."""
    safe_mount('/training_data', 'GET', get_training_data)
    safe_mount('/training_data', 'OPTIONS', get_training_data)
    safe_mount('/submit_training', 'POST', submit_training)
    safe_mount('/submit_training', 'OPTIONS', submit_training)
    safe_mount('/brain/memory', 'GET', get_brain_memory)
    safe_mount('/brain/memory', 'OPTIONS', get_brain_memory)
    safe_mount('/brain/memory/<context_hash>', 'DELETE', delete_brain_memory)
    safe_mount('/brain/memory/<context_hash>', 'OPTIONS', delete_brain_memory)
