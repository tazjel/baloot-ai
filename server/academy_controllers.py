import os
import json
import glob
from py4web import action, request, response, abort
from server.puzzle_schema import Puzzle
from server.logging_utils import logger

# Base directory for puzzles
# Assuming this file is in server/academy_controllers.py
# Puzzles are in server/content/puzzles
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUZZLE_DIR = os.path.join(BASE_DIR, 'content', 'puzzles')

@action('academy/puzzles', method=['GET', 'OPTIONS'])
def list_puzzles():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    logger.debug("[Academy] Listing puzzles...")
    puzzles = []
    # Find all .json files in PUZZLE_DIR
    search_path = os.path.join(PUZZLE_DIR, '*.json')
    files = glob.glob(search_path)

    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Lite validation/parsing
                # We return a summary
                puzzles.append({
                    "id": data.get('id'),
                    "title": data.get('title'),
                    "difficulty": data.get('difficulty'),
                    "tags": data.get('tags', [])
                })
        except Exception as e:
            logger.error(f"[Academy] Error loading puzzle {fpath}: {e}")

    logger.debug(f"[Academy] Found {len(puzzles)} puzzles.")
    return {"puzzles": puzzles}


@action('academy/puzzles/<puzzle_id>', method=['GET', 'OPTIONS'])
def get_puzzle(puzzle_id):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    logger.info(f"[Academy] Fetching puzzle: {puzzle_id}")
    # Sanitize puzzle_id to prevent directory traversal
    safe_id = "".join([c for c in puzzle_id if c.isalnum() or c in ('_', '-')])
    fpath = os.path.join(PUZZLE_DIR, f"{safe_id}.json")

    if not os.path.exists(fpath):
        logger.warning(f"[Academy] Puzzle not found: {fpath}")
        response.status = 404
        return {"error": "Puzzle not found"}

    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure strictly follows schema (optional)
            puzzle = Puzzle.from_dict(data)
            # Return raw data for now as dataclass json serialization might need helper
            return {"puzzle": data} 
    except Exception as e:
        logger.error(f"[Academy] Failed to load puzzle {puzzle_id}: {str(e)}")
        response.status = 500
        return {"error": f"Failed to load puzzle: {str(e)}"}

@action('academy/verify', method=['POST', 'OPTIONS'])
def verify_solution():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    puzzle_id = data.get('puzzleId')
    user_moves = data.get('moves', []) # List of card strings e.g. ["KH"]
    logger.info(f"[Academy] Verifying solution for {puzzle_id}. Moves: {user_moves}")

    if not puzzle_id or not user_moves:
        return {"error": "Invalid payload"}

    # Load Puzzle
    safe_id = "".join([c for c in puzzle_id if c.isalnum() or c in ('_', '-')])
    fpath = os.path.join(PUZZLE_DIR, f"{safe_id}.json")
    
    if not os.path.exists(fpath):
        return {"error": "Puzzle not found"}

    with open(fpath, 'r', encoding='utf-8') as f:
        pdata = json.load(f)
    
    solution = pdata.get('solution', {})
    
    success = False
    message = "Incorrect sequence."

    if solution.get('type') == 'sequence':
        expected = solution.get('data', [])
        # Simple strict equality check for sequence
        # We might want prefix checking (if user is mid-sequence) but usually verification is at end?
        # Or per-move?
        # Let's assume this is "Check Full Solution"
        if user_moves == expected:
            success = True
            message = "Correct!"
        else:
            # Check partial
            if len(user_moves) <= len(expected):
                if user_moves == expected[:len(user_moves)]:
                     success = True
                     message = "Good move, keep going..."
                else:
                     message = f"Wrong move. Expected {expected[len(user_moves)-1]} but got {user_moves[-1]}."
    
    logger.info(f"[Academy] Verification result: {success} ({message})")
    return {"success": success, "message": message}
