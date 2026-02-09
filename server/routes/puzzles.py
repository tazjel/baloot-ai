"""
Puzzle routes: list and detail for AI Classroom.
"""
import os
import json
from py4web import action, request, response
from server.common import logger


@action('puzzles', method=['GET', 'OPTIONS'])
def get_puzzles():
    """List available AI Classroom Puzzles."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        APP_FOLDER = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        puzzle_path = os.path.join(APP_FOLDER, 'ai_worker', 'benchmarks', 'golden_puzzles.json')

        if not os.path.exists(puzzle_path):
            return {"puzzles": []}

        with open(puzzle_path, 'r', encoding='utf-8') as f:
            puzzles = json.load(f)

        summary = [{
            "id": p.get('id'),
            "difficulty": p.get('difficulty'),
            "description": p.get('description'),
            "context_hash": p.get('context_hash')
        } for p in puzzles]

        return {"puzzles": summary}

    except Exception as e:
        logger.error(f"Failed to fetch puzzles: {e}")
        return {"error": str(e)}


@action('puzzles/<puzzle_id>', method=['GET', 'OPTIONS'])
def get_puzzle_detail(puzzle_id):
    """Get full detail for a specific puzzle."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        APP_FOLDER = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        puzzle_path = os.path.join(APP_FOLDER, 'ai_worker', 'benchmarks', 'golden_puzzles.json')

        if not os.path.exists(puzzle_path):
            response.status = 404
            return {"error": "Puzzle database not found"}

        with open(puzzle_path, 'r', encoding='utf-8') as f:
            puzzles = json.load(f)

        puzzle = next((p for p in puzzles if p.get('id') == puzzle_id), None)

        if not puzzle:
            response.status = 404
            return {"error": "Puzzle not found"}

        return {"puzzle": puzzle}

    except Exception as e:
        logger.error(f"Failed to fetch puzzle {puzzle_id}: {e}")
        return {"error": str(e)}


def bind_puzzles(safe_mount):
    """Bind puzzle routes to the app."""
    safe_mount('/puzzles', 'GET', get_puzzles)
    safe_mount('/puzzles', 'OPTIONS', get_puzzles)
    safe_mount('/puzzles/<puzzle_id>', 'GET', get_puzzle_detail)
    safe_mount('/puzzles/<puzzle_id>', 'OPTIONS', get_puzzle_detail)
