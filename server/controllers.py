"""
This file defines actions, i.e. functions the URLs are mapped into
The @action(path) decorator exposed the function at URL:

    http://127.0.0.1:8000/{app_name}/{path}

If app_name == '_default' then simply

    http://127.0.0.1:8000/{path}

If path == 'index' it can be omitted:

    http://127.0.0.1:8000/

The path follows the bottlepy syntax.

@action.uses('generic.html')  indicates that the action uses the generic.html template
@action.uses(session)         indicates that the action uses the session
@action.uses(db)              indicates that the action uses the db
@action.uses(T)               indicates that the action uses the i18n & pluralization
@action.uses(auth.user)       indicates that the action requires a logged in user
@action.uses(auth)            indicates that the action requires the auth object

session, db, T, auth, and tempates are examples of Fixtures.
Warning: Fixtures MUST be declared with @action.uses({fixtures}) else your app will result in undefined behavior
"""

import bcrypt
import os
import mimetypes
from py4web import action, request, response, abort
from server.common import db, logger, redis_client
import server.auth_utils as auth_utils
from ai_worker.llm_client import GeminiClient
from server.room_manager import room_manager

def token_required(f):
    def decorated(*args, **kwargs):
        # Extract the token from the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            abort(401, 'Authorization token is missing or invalid')

        token = auth_header.split(" ")[1]  # Extract the token part
        
        payload = auth_utils.verify_token(token)
        if not payload:
             abort(401, 'Invalid or Expired Token')
             
        request.user = payload  # You can attach user information to the request
        return f(*args, **kwargs)

    return decorated


@action('user', method=['GET'])
@token_required
def user():
    """Example of a protected endpoint that requires a valid JWT token to be included in the Authorization header."""
    response.status = 200
    response.status = 200
    user_record = db.app_user(request.user.get('user_id'))
    points = user_record.league_points if user_record else 1000
    
    # Simple Tier Logic
    tier = "Bronze"
    if points >= 2000: tier = "Grandmaster"
    elif points >= 1800: tier = "Diamond"
    elif points >= 1600: tier = "Platinum"
    elif points >= 1400: tier = "Gold"
    elif points >= 1200: tier = "Silver"
    
    return {"user": request.user, "leaguePoints": points, "tier": tier}


@action('signup', method=['POST', 'OPTIONS'])
@action.uses(db)
def signup():
    # Get credentials from the request.
    data = request.json
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    password= data.get('password')  
    email = data.get('email')

    print(f"{email} is signing up!")

    # Check if the user already exists.
    existing_user = db(db.app_user.email == email).select().first()
    if (existing_user):
        response.status = 409
        return {"error": "User already exists"}

    # Hash the password.
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Create new user record in the database.
    user_id = db.app_user.insert(first_name=first_name, last_name=last_name, email=email, password=hashed_password)

    response.status = 201
    return {"message": "User registered successfully", "email": email, "firstName": first_name, "lastName": last_name, "user_id": user_id}


@action('signin', method=['POST'])
def signin():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    print("User is signing in!")

    if not email or not password:
        return {"error": "Email and password are required"}

    # Retrieve user from the database
    user = db(db.app_user.email == email).select().first()

    if not user:
        print("user not found!")
        response.status = 404
        return {"error": "User not found"}

    # Check if the supplied password matches the hashed password in the database
    if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        # Create a JWT token
        token = auth_utils.generate_token(user.id, user.email, user.first_name, user.last_name)
        response.status = 200
        return {"email": user.email, "firstName": user.first_name, "lastName": user.last_name, "token": token}
        
    return {"error": "Invalid credentials"}


@action('save_score', method=['POST'])
@token_required
@action.uses(db)
def save_score():
    data = request.json
    score_us = data.get('scoreUs')
    score_them = data.get('scoreThem')
    user_id = request.user.get('user_id')
    
    # Retrieve user email for linkage
    user = db.app_user(user_id)
    if not user:
        response.status = 404
        return {"error": "User not found"}
        
    db.game_result.insert(
        user_email=user.email,
        score_us=score_us,
        score_them=score_them,
        is_win=(score_us > score_them)
    )
    
    # Update League Points
    points_change = 25 if (score_us > score_them) else -15
    new_points = max(0, (user.league_points or 1000) + points_change)
    user.update_record(league_points=new_points)
    
    return {"message": "Score saved successfully"}


@action('leaderboard', method=['GET'])
@action.uses(db)
def leaderboard():
    # Simple leaderboard: Top 10 wins (count of wins per email)
    # This is a bit complex in pure pydal without raw SQL for grouping sometimes,
    # let's just return recent games for now for simplicity.
    # Sort by League Points
    top_players = db(db.app_user).select(orderby=~db.app_user.league_points, limitby=(0, 10))
    return {"leaderboard": [p.as_dict() for p in top_players]}


@action('index')
def catch_all(path=None):
    print("default page being served")
    # Construct an absolute path to the React index.html file.
    SERVER_FOLDER = os.path.dirname(__file__)
    PROJECT_ROOT = os.path.dirname(SERVER_FOLDER)
    file_path = os.path.join(PROJECT_ROOT, 'static', 'build', 'index.html')

    # Ensure the file exists
    if not os.path.isfile(file_path):
        # Handle the error appropriately (e.g., return a 404 page)
        return f'File not found: {file_path}', 404

    with open(file_path, 'rb') as f:
        response.headers['Content-Type'] = 'text/html'
        return f.read()
        


@action('training_data', method=['GET', 'OPTIONS'])
@action.uses(db)
def get_training_data():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    if request.method == 'OPTIONS':
        return ""
        
    logger.debug(f"[DEBUG] fetch training_data")
    rows = db(db.bot_training_data).select(orderby=~db.bot_training_data.created_on, limitby=(0, 50))
    logger.debug(f"[DEBUG] returning {len(rows)} training examples")
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
    logger.debug(f"[DEBUG] submit_training payload: {data.keys()}")
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
        
        r = redis_client
        
        # Scan for learned moves: brain:correct:*
        keys = r.keys("brain:correct:*")
        
        memory = []
        if keys:
            # Pipelined get for performance
            pipe = r.pipeline()
            for k in keys:
                pipe.get(k)
            values = pipe.execute()
            
            for k, v in zip(keys, values):
                if v:
                    import json
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

        r = redis_client
        
        key = f"brain:correct:{context_hash}"
        r.delete(key)
        
        return {"success": True, "message": f"Deleted {key}"}
    except Exception as e:
        return {"error": str(e)}


@action('analyze_screenshot', method=['POST', 'OPTIONS'])
def analyze_screenshot():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    # Ensure dataset directory exists
    import os
    import uuid
    from server.settings import UPLOAD_FOLDER
    dataset_dir = os.path.join(UPLOAD_FOLDER, 'dataset')
    os.makedirs(dataset_dir, exist_ok=True)

    if request.method == 'OPTIONS':
        return ""

    if not request.files.get('screenshot'):
        response.status = 400
        return {"error": "No screenshot file provided"}

    f = request.files['screenshot']
    # Read file content
    image_data = f.file.read()
    
    # Save the file (Data Flywheel)
    ext = mimetypes.guess_extension(f.content_type) or ".jpg"
    filename = f"img_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(dataset_dir, filename)
    
    with open(filepath, 'wb') as saved_file:
        saved_file.write(image_data)
    
    logger.debug(f"[DEBUG] Saved dataset image to {filepath}")
    logger.debug(f"[DEBUG] Analyzing screenshot. Size: {len(image_data)} bytes. Content-Type: {f.content_type}")
    logger.debug(f"[DEBUG] API Key present? {bool(os.environ.get('GEMINI_API_KEY'))}")

    # Debug Logging to File
    debug_log_path = os.path.join("logs", "gemini_debug.log")
    with open(debug_log_path, "a") as logutils:
        logutils.write(f"\n[REQ] Analyze Screenshot. Size: {len(image_data)}\n")
        logutils.write(f"[REQ] API Key Present: {bool(os.environ.get('GEMINI_API_KEY'))}\n")

    # Initialize Gemini
    try:
        gemini = GeminiClient()
        # raise Exception("AI Service Disabled")
        # Fallback to image/jpeg if content_type is missing
        mime = f.content_type if f.content_type else 'image/jpeg'
        
        result = None
        if mime.startswith('video/'):
            logger.debug(f"[DEBUG] Processing Video: {mime}")
            with open(debug_log_path, "a") as logutils:
                 logutils.write(f"[REQ] Processing Video: {mime}\n")
            result = gemini.analyze_video(filepath, mime_type=mime)
        else:
            result = gemini.analyze_image(image_data, mime_type=mime)
        
        with open(debug_log_path, "a") as logutils:
             logutils.write(f"[RES] Result: {str(result)[:100]}...\n")
             
        if result:
            return {"data": result, "imageFilename": filename}
        else:
            with open(debug_log_path, "a") as logutils:
                logutils.write("[ERR] Gemini returned None\n")
            print("[DEBUG] Gemini returned None result")
            response.status = 500
            return {"error": "Gemini returned empty result (check logs)"}
    except Exception as e:
        with open(debug_log_path, "a") as logutils:
            logutils.write(f"[EXC] Exception: {e}\n")
        print(f"[DEBUG] Exception in analyze_screenshot: {e}")
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

    # --- Transform AIStudio State to LLM Context ---
    # AIStudio State: 
    # { players: [...], bid: {type, suit}, playedCards: {...} }
    
    bid = game_state.get('bid', {})
    mode = bid.get('type', 'SUN')
    trump = bid.get('suit')
    
    # Extract Hand (Assume Player 0 / Bottom is User)
    players = game_state.get('players', [])
    me = next((p for p in players if p['name'] == 'Me' or p['position'] == 'Bottom'), None)
    
    hand_strs = []
    if me:
        # hand is list of {rank, suit}
        hand_strs = [f"{c['rank']}{c['suit']}" for c in me.get('hand', [])]

    # Extract Table Cards (Current Trick)
    played_map = game_state.get('playedCards', {})
    table_strs = [f"{c['rank']}{c['suit']}" for c in played_map.values()]
    
    context = {
        'mode': mode,
        'trump': trump,
        'hand': hand_strs,
        'table': table_strs,
        'played_cards': [], # Full history not yet tracked in Studio Builder
        'position': 'Bottom'
    }
    
    logger.debug(f"[DEBUG] ask_strategy context: {context}")

    # --- RAG Lite: Retrieve Relevant Examples ---
    examples = []
    try:
         # Fetch recent training data (limit 20)
         rows = db(db.bot_training_data).select(orderby=~db.bot_training_data.created_on, limitby=(0, 20))
         for r in rows:
             # Basic Filtering: Check if example matches current Game Mode
             # We store gameState as JSON string. 
             # Parsing every row might be slow if DB is huge, but fine for 20.
             try:
                 example_state = r.game_state_json
                 # Quick string check to avoid parsing mismatch
                 if mode and mode in example_state: 
                     examples.append({
                         "state": example_state,
                         "correct_move": r.correct_move_json,
                         "reason": r.reason
                     })
             except: continue
             
             if len(examples) >= 3: break # Limit to 3 examples
    except Exception as e:
        logger.error(f"Failed to retrieve training examples: {e}")

    try:
        gemini = GeminiClient()
        # raise Exception("AI Service Disabled")
        # Analyze with Examples
        result = gemini.analyze_hand(context, examples=examples)
        if result:
            logger.debug(f"[DEBUG] ask_strategy result: {result}")
            return {"recommendation": result}
        else:
            return {"error": "AI could not determine a move."}
    except Exception as e:
        print(f"Ask Strategy Error: {e}")
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
    
    debug_log_path = os.path.join("logs", "gemini_debug.log")
    with open(debug_log_path, "a") as f:
         f.write(f"\n[REQ] Generate Scenario: {text}\n")
         
    try:
         gemini = GeminiClient()
         # raise Exception("AI Service Disabled")
         result = gemini.generate_scenario_from_text(text)
         
         with open(debug_log_path, "a") as f:
              f.write(f"[RES] Scenario Generated: {str(result)[:100]}...\n")
              
         return {"data": result}
    except Exception as e:
         with open(debug_log_path, "a") as f:
              f.write(f"[ERR] Generate Scenario Failed: {e}\n")
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
    
    debug_log_path = os.path.join("logs", "gemini_debug.log")
    with open(debug_log_path, "a") as f:
         f.write(f"\n[REQ] Analyze Match: {game_id}\n")

    try:
         # Fetch Match History
         game = room_manager.get_game(game_id)
         if not game:
              # Try to find archived game if needed, but only memory for now
              return {"error": "Game not found in memory"}
              
         history = game.full_match_history
         
         
         gemini = GeminiClient()
         # raise Exception("AI Service Disabled")
         result = gemini.analyze_match_history(history)
         
         with open(debug_log_path, "a") as f:
              f.write(f"[RES] Match Analysis: {str(result)[:100]}...\n")
              
         return {"analysis": result}
    except Exception as e:
         with open(debug_log_path, "a") as f:
              f.write(f"[ERR] Match Analysis Failed: {e}\n")
         return {"error": str(e)}


@action('ai_thoughts/<game_id>', method=['GET', 'OPTIONS'])
def get_ai_thoughts(game_id):
    """
    Fetch live AI thoughts for a running game.
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        if not redis_client:
             return {"thoughts": {}}

        r = redis_client
        
        # Scan for thoughts: bot:thought:{game_id}:{player_index}
        pattern = f"bot:thought:{game_id}:*"
        keys = r.keys(pattern)
        
        thoughts = {}
        if keys:
            values = r.mget(keys)
            for k, v in zip(keys, values):
                # extract player index from key
                # key format: bot:thought:GAMEID:INDEX
                try:
                    idx = int(k.split(':')[-1])
                    if v:
                         thoughts[idx] = json.loads(v)
                except:
                    pass
                    
        return {"thoughts": make_serializable(thoughts)}

    except Exception as e:
        logger.error(f"Failed to fetch thoughts: {e}")
        return {"thoughts": {}}


@action('match_history/<game_id>', method=['GET', 'OPTIONS'])
def get_match_history(game_id):
    """
    Fetch full match history for Time Travel replay.
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    if request.method == 'OPTIONS':
        return ""
        
    try:
        game = room_manager.get_game(game_id)
        if not game:
            # Try DB
            record = db.match_archive(game_id=game_id)
            if record and record.history_json:
                 import json
                 try:
                     return {"history": json.loads(record.history_json)}
                 except:
                     pass
            
            response.status = 404
            return {"error": "Game not found"}
            
        return {"history": make_serializable(game.full_match_history)}
    except Exception as e:
        logger.error(f"Error in get_match_history: {e}")
        import traceback
        traceback.print_exc()
        response.status = 500
        return {"error": f"Internal Error: {str(e)}"}

def make_serializable(obj):
    """
    Recursively converts objects to JSON-serializable formats.
    Handles Enums, Objects with to_dict, and datetimes.
    """
    from enum import Enum
    import datetime
    
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(v) for v in obj]
    elif isinstance(obj, tuple):
        return [make_serializable(v) for v in obj]
    elif isinstance(obj, Enum):
        return obj.value
    elif hasattr(obj, 'to_dict'):
        return make_serializable(obj.to_dict())
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return str(obj)
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        return str(obj)


@action('puzzles', method=['GET', 'OPTIONS'])
def get_puzzles():
    """
    List available AI Classroom Puzzles.
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        import json
        # Locate the benchmarks file
        APP_FOLDER = os.path.dirname(os.path.dirname(__file__)) # Root
        puzzle_path = os.path.join(APP_FOLDER, 'ai_worker', 'benchmarks', 'golden_puzzles.json')
        
        if not os.path.exists(puzzle_path):
             return {"puzzles": []}
             
        with open(puzzle_path, 'r', encoding='utf-8') as f:
             puzzles = json.load(f)
             
        # Return summary list
        summary = []
        for p in puzzles:
             summary.append({
                 "id": p.get('id'),
                 "difficulty": p.get('difficulty'),
                 "description": p.get('description'),
                 "context_hash": p.get('context_hash')
             })
             
        return {"puzzles": summary}
        
    except Exception as e:
        logger.error(f"Failed to fetch puzzles: {e}")
        return {"error": str(e)}

@action('puzzles/<puzzle_id>', method=['GET', 'OPTIONS'])
def get_puzzle_detail(puzzle_id):
    """
    Get full detail for a specific puzzle.
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        import json
        APP_FOLDER = os.path.dirname(os.path.dirname(__file__))
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

@action('game/director/update', method=['POST', 'OPTIONS'])
def update_director_config():
    """
    Updates the active game settings and player configs (Commissioner's Desk).
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    game_id = data.get('gameId')
    settings = data.get('settings') # Dict of global settings (e.g. strictMode)
    bot_configs = data.get('botConfigs') # Dict { playerIndex: { strategy, profile } }
    
    if not game_id:
        response.status = 400
        return {"error": "Missing gameId"}

    try:
        from server.room_manager import room_manager
        game = room_manager.get_game(game_id)
        if not game:
            response.status = 404
            return {"error": "Game not found"}
            
        logger.info(f"[DIRECTOR] Updating Game {game_id}")
        
        # 1. Update Global Settings
        # GameSettings is a Pydantic model usually, or simple dict? 
        # In types.ts it's interface. In game.py it uses settings dict usually or defaults.
        # Let's inspect game.settings structure. 
        # Ideally we update the existing object.
        if settings:
            logger.info(f"[DIRECTOR] Update Settings: {settings}")
            if hasattr(game, 'settings'):
                # Merge
                for k, v in settings.items():
                    # Sanitize Types if needed
                    if hasattr(game.settings, k):
                        setattr(game.settings, k, v)
                    elif isinstance(game.settings, dict):
                         game.settings[k] = v
            else:
                 # If game.settings doesn't exist, create it (legacy games)
                 game.settings = settings
                 
        # 2. Update Bot Configs
        if bot_configs:
            logger.info(f"[DIRECTOR] Update Bots: {bot_configs}")
            for idx_str, cfg in bot_configs.items():
                idx = int(idx_str)
                if 0 <= idx < len(game.players):
                    p = game.players[idx]
                    
                    if 'strategy' in cfg:
                        p.strategy = cfg['strategy'] # e.g. 'neural', 'mcts'
                        
                    if 'profile' in cfg:
                        # Translate 'Aggressive' -> Personality dict? 
                        # Or just store string and let Agent parse it?
                        # Agent uses p.name usually. But we want override.
                        # Let's check Agent logic. It uses p.strategy (we added that).
                        # It parses p.name for personality. 
                        # We should add p.profile attribute support to Agent.
                        p.profile = cfg['profile'] # 'Aggressive', 'Conservative'

        return {"success": True, "message": "Director Config Applied"}

    except Exception as e:
        logger.error(f"Director Update Failed: {e}")
        import traceback
        traceback.print_exc()
        response.status = 500
        return {"error": str(e)}

@action('api/mind/inference/<game_id>', method=['GET', 'OPTIONS'])
def get_mind_inference(game_id):
    """
    Fetch "Theory of Mind" probabilities for 3D visualization.
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        if not redis_client:
             return {"mind_map": {}}

        r = redis_client
        
        # Scan for mind maps: bot:mind_map:{game_id}:{player_index}
        pattern = f"bot:mind_map:{game_id}:*"
        keys = r.keys(pattern)
        
        mind_map = {}
        if keys:
            values = r.mget(keys)
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

# --- Explicit Binding for Custom Runner ---
from py4web.core import bottle

def bind(app):
    """
    Explicitly bind all controller actions to the main Bottle app instance.
    This bypasses py4web's auto-discovery which fails in this custom environment.
    """
    import os
    
    with open("logs/import_debug.txt", "a") as f:
        f.write(f"DEBUG: Binding Main Controllers to App {id(app)}\n")
        
        # Idempotency Guard
        if getattr(app, '_main_controllers_bound', False):
            f.write("DEBUG: Main Controllers already bound. Skipping.\n")
            return
            
        def safe_mount(path, method, callback):
            try:
                app.route(path, method=method, callback=callback)
                f.write(f"DEBUG: Mounted {path} [{method}]\n")
            except Exception as e:
                f.write(f"DEBUG: Failed to mount {path}: {e}\n")

        # 1. Static Files
        # We need to serve /static/... from the actual static folder (Project Root/static)
        SERVER_FOLDER = os.path.dirname(__file__)
        PROJECT_ROOT = os.path.dirname(SERVER_FOLDER)
        STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'static')
        
        f.write(f"DEBUG: Serving Static from {STATIC_FOLDER} (Exists? {os.path.exists(STATIC_FOLDER)})\n")
        
        def serve_static(filepath):
            return bottle.static_file(filepath, root=STATIC_FOLDER)
            
        safe_mount('/static/<filepath:path>', 'GET', serve_static)

        # 2. Auth & User
        safe_mount('/user', 'GET', user)
        safe_mount('/signup', 'POST', signup)
        safe_mount('/signup', 'OPTIONS', signup)
        safe_mount('/signin', 'POST', signin)
        
        # 3. Game & Score
        safe_mount('/save_score', 'POST', save_score)
        safe_mount('/leaderboard', 'GET', leaderboard)
        
        # 4. AI / Brain / Training
        safe_mount('/training_data', 'GET', get_training_data)
        safe_mount('/training_data', 'OPTIONS', get_training_data)
        
        safe_mount('/submit_training', 'POST', submit_training)
        safe_mount('/submit_training', 'OPTIONS', submit_training)
        
        safe_mount('/brain/memory', 'GET', get_brain_memory)
        safe_mount('/brain/memory', 'OPTIONS', get_brain_memory)
        
        safe_mount('/brain/memory/<context_hash>', 'DELETE', delete_brain_memory)
        safe_mount('/brain/memory/<context_hash>', 'OPTIONS', delete_brain_memory)
        
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
        
        safe_mount('/match_history/<game_id>', 'GET', get_match_history)
        safe_mount('/match_history/<game_id>', 'OPTIONS', get_match_history)
        
        safe_mount('/puzzles', 'GET', get_puzzles)
        safe_mount('/puzzles', 'OPTIONS', get_puzzles)
        
        safe_mount('/puzzles/<puzzle_id>', 'GET', get_puzzle_detail)
        safe_mount('/puzzles/<puzzle_id>', 'OPTIONS', get_puzzle_detail)

        # 6. Director / Commissioner
        safe_mount('/game/director/update', 'POST', update_director_config)
        safe_mount('/game/director/update', 'OPTIONS', update_director_config)

        # 7. Mind Map (3D)
        safe_mount('/api/mind/inference/<game_id>', 'GET', get_mind_inference)
        safe_mount('/api/mind/inference/<game_id>', 'OPTIONS', get_mind_inference)

        # 5. Index / Catch-All
        # This must be LAST/LOW PRIORITY usually, or ensure specific routes match first.
        # Bottle matches longest prefix usually.
        safe_mount('/', 'GET', catch_all)
        safe_mount('/index', 'GET', catch_all)
        safe_mount('/<path:path>', 'GET', catch_all) # Wildcard for SPA Routing
        
        setattr(app, '_main_controllers_bound', True)

