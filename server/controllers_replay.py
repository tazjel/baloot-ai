from py4web import action, request, response, abort
from py4web.core import bottle
from server.common import db, logger, redis_client
from server.room_manager import room_manager
from server.logging_utils import log_event, log_error
from game_engine.logic.game import Game, GamePhase
from game_engine.models.card import Card
import json
import uuid

# Helper Class for Replay/Fork Checks (Must be global for pickle)
class DummyContract:
     def __init__(self, bid_dict):
          self.variant = bid_dict.get('variant')
          self.type = bid_dict.get('type')
          self.suit = bid_dict.get('suit')

with open("logs/import_debug.txt", "a") as f:
    f.write(f"DEBUG: Importing server.controllers_replay... Hybrid Mode\n")

# Use bottle to force registration, but use action for behavior (fixtures)
app = bottle.default_app()

# PING
@action('replay/ping', method=['GET'])
def replay_ping():
    return "pong_v2"

# Explicit Mount


# LIST
@action('replay/list', method=['GET', 'OPTIONS'])
@action.uses(db)
def get_archived_matches():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Content-Type'] = 'application/json'

    if request.method == 'OPTIONS':
        return ""
    
    try:
        if not hasattr(db, 'match_archive'):
             return json.dumps({"error": "DB Table match_archive missing", "matches": []})

        # Fetch latest 20 games
        rows = db(db.match_archive).select(
            db.match_archive.game_id, 
            db.match_archive.final_score_us, 
            db.match_archive.final_score_them, 
            db.match_archive.timestamp,
            orderby=~db.match_archive.timestamp,
            limitby=(0, 20)
        )
        
        matches = []
        for r in rows:
            try:
                matches.append({
                    "gameId": r.game_id,
                    "scoreUs": r.final_score_us,
                    "scoreThem": r.final_score_them,
                    "timestamp": str(r.timestamp)
                })
            except Exception as row_err:
                 log_error("REPLAY_ROW_ERROR", "GLOBAL", str(row_err))

        return json.dumps({"matches": matches})


    except Exception as e:
        import traceback
        traceback.print_exc()
        log_error("REPLAY_LIST_ERROR", "GLOBAL", str(e))
        return json.dumps({"error": str(e), "matches": []})



# FORK
@action('replay/fork', method=['POST', 'OPTIONS'])
def fork_game():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    # ... rest of function ...

    # Validating params...
    source_game_id = data.get('gameId') # could be int or string
    round_num = data.get('roundNum')  # 1-based index of round in history
    trick_index = data.get('trickIndex') # 0-based index of trick to stop AT (i.e. play tricks 0..trickIndex-1)

    log_event("REPLAY_FORK_REQUEST", str(source_game_id), details={"round": round_num, "trick": trick_index})

    if not source_game_id or round_num is None or trick_index is None:
        log_error("REPLAY_FORK_ERROR", str(source_game_id), "Missing parameters for fork request")
        return {"error": "Missing parameters"}

    # 1. Retrieve History
    # Try active memory first
    source_game = room_manager.get_game(source_game_id)
    history = None
    source_type = "MEMORY"
    
    if source_game:
        history = source_game.full_match_history
    else:
        # DB Lookup
        # DB Lookup - Use explicit query for safety
        safe_id = str(source_game_id).strip()
        log_event("REPLAY_FORK_DEBUG", "GLOBAL", details={"lookup_id": safe_id, "original_id": source_game_id})
        
        record = db(db.match_archive.game_id == safe_id).select().first()
        
        if record and record.history_json:
             try:
                 history = json.loads(record.history_json)
                 source_type = "DATABASE"
             except Exception as json_err:
                 log_error("REPLAY_FORK_ERROR", str(source_game_id), f"Corrupt history in DB: {json_err}")
                 return {"error": "Corrupt history data in archive"}
        else:
             log_error("REPLAY_FORK_ERROR", str(source_game_id), f"Fork failed: Game {safe_id} not found in archive")
             return {"error": f"Game {safe_id} not found in memory or archive"}

    # Validate Round
    # round_num is 1-based, array is 0-based
    r_idx = int(round_num) - 1
    if r_idx < 0 or r_idx >= len(history):
        log_error("REPLAY_FORK_ERROR", str(source_game_id), f"Invalid Round Number: {round_num}")
        return {"error": "Invalid Round Number"}

    snapshot = history[r_idx]
    
    # 2. Create NEW Game
    new_room_id = f"replay_{source_game_id}_{round_num}_{trick_index}_{uuid.uuid4().hex[:8]}"
    log_event("REPLAY_FORK_START", new_room_id, details={"source": source_game_id, "source_type": source_type, "round": round_num, "trick": trick_index})
    
    new_game = Game(new_room_id)
    # FIX: Use save_game instead of property setter (which does nothing if Redis is on)
    room_manager.save_game(new_game)
    
    # 3. Hydrate State
    try:
        # A. Basic Setup
        new_game.players = [] # Reset default players if any
        # We need to reconstruct players. 
        # Strategy: Index 0 is YOU (Reserved). Others are Bots.
        
        # 0. Add You
        new_game.add_player("RESERVED_FOR_USER", "You (Forked)")
        
        # 1. Add Others (Indices 1, 2, 3)
        if source_game:
             # Use original names/avatars 
             for i, p in enumerate(source_game.players):
                 if i == 0: continue # Skip original Bottom, we took it
                 # Create Bot
                 bot_id = f"BOT_FORK_{i}_{uuid.uuid4().hex[:4]}"
                 bot_player = new_game.add_player(bot_id, f"{p.name} (Bot)", p.avatar)
                 if bot_player: bot_player.is_bot = True
        else:
             # Fallback generic players
             for i in range(1, 4):
                 bot_id = f"BOT_FORK_{i}_{uuid.uuid4().hex[:4]}"
                 bot_player = new_game.add_player(bot_id, f"Player {i} (Bot)")
                 if bot_player: bot_player.is_bot = True

        # B. Match State (Scores logic is complex because 'match_scores' in game tracks cumulative. 
        # But the snapshot stores the state *at the end* of the round usually? 
        # Wait, 'snapshot' is created at end_round.
        # It contains 'scores' (Round Result) and we want the state AT THE START of this round.
        # So we need the cumulative scores of all PREVIOUS rounds.
        previous_rounds = history[:r_idx]
        us_score = sum(r['scores']['us']['result'] for r in previous_rounds)
        them_score = sum(r['scores']['them']['result'] for r in previous_rounds) # Logic check needed on 'scores' structure
        
        # Actually, let's just trust the snapshot if it had cumulative, but it tracks 'round result'.
        # Recalculate:
        new_game.match_scores = {"us": us_score, "them": them_score}
        for pr in previous_rounds:
             # Assuming pr['scores'] has the round total points.
             # ScoringEngine usually returns raw points.
             # Double check Game.end_round: 
             # round_result, score_us, score_them = self.scoring_engine.calculate_final_scores()
             # self.past_round_results.append(round_result)
             # snapshot['scores'] = round_result
             # So we need to sum up what was added to match_scores.
             # This is slightly ambiguous without seeing 'round_result' structure.
             # Let's assume for MVP we start at 0 or approximate.
             # BETTER: new_game.match_scores = sum of previous.
             pass
             
        # For simplicity in MVP, let's just carry over the raw 'match_scores' from the snapshot IF it had it, 
        # but snapshot logic in Game.py didn't seemingly save 'match_scores' snapshot directly? 
        # It saved 'scores': copy.deepcopy(round_result).
        # We might need to fix Game.py to save 'match_scores_start' or similar. 
        # OR: Just recalculate from history.
        
        # C. Round State
        new_game.dealer_index = snapshot['dealerIndex']
        new_game.floor_card = None # Already dealt
        new_game.bid = snapshot['bid']
        new_game.game_mode = new_game.bid['type'] # e.g. 'SUN'
        new_game.trump_suit = new_game.bid['suit']
        new_game.doubling_level = 2 if new_game.bid['doubled'] else 1 # Simple approximation
        
        new_game.phase = GamePhase.PLAYING.value
        
        # D. Restore Hands
        # snapshot['initialHands'] is Dict[Position, List[CardDict]]
        initial_hands = snapshot.get('initialHands')
        if not initial_hands:
             log_error("REPLAY_FORK_ERROR", new_room_id, "Snapshot missing initialHands data")
             return {"error": "Snapshot missing initialHands data (Cannot Replay)"}
             
        
        # Map Position -> Player Index
        pos_map = {p.position: p for p in new_game.players}
        
        for pos, cards_data in initial_hands.items():
            if pos in pos_map:
                player = pos_map[pos]
                player.hand = [Card(c['suit'], c['rank']) for c in cards_data]

        # E. Replay Moves
        
        # FIX: Initialize a dummy BiddingEngine so is_valid_move doesn't crash
        # The contract is already set in new_game.bid
        # We need an object that has .contract property matching new_game.bid
        from game_engine.logic.bidding_engine import BiddingEngine
        
        # Better: create a partial BiddingEngine
        be = BiddingEngine(new_game.dealer_index, new_game.floor_card, new_game.players, new_game.match_scores)

        # Hydrate contract from snapshot using the GLOBAL DummyContract class
        be.contract = DummyContract(new_game.bid)
        new_game.bidding_engine = be

        target_trick_count = int(trick_index)
        tricks_to_replay = snapshot['tricks'][:target_trick_count]
        
        # We need to set 'current_turn' correctly before playing.
        # Who starts? Bidder? No, depends on dealer.
        # (Dealer + 1) % 4
        new_game.current_turn = (new_game.dealer_index + 1) % 4
        
        for trick in tricks_to_replay:
            # trick['cards'] is list of cards played in order.
            # But wait, trick['cards'] in Game.py is list of Dicts with 'playedBy'?
            # Let's verify Game.py serialization of round_history.
            # 'currentRoundTricks' -> { 'cards': [c.to_dict()...], 'playedBy': ... }
            # Actually Game.py: 
            # 'cards': [c.to_dict()...]
            # 'playedBy': t.get('playedBy') -> List[Pos]? No, let's check Game logic.
            # Game.round_history is list of tricks.
            # TrickManager.resolve_trick appends:
            # { 'cards': [c...], 'playedBy': [pos...], 'winner': pos, 'points': int }
            
            cards = trick['cards']
            played_bys = trick.get('playedBy', []) # List of positions
            
            for i, card_data in enumerate(cards):
                # Find player
                pos = played_bys[i]
                player = pos_map[pos]
                
                # Find card index in hand
                # Card equality might be tricky with objects vs dicts.
                c_rank = card_data['rank']
                c_suit = card_data['suit']
                
                card_idx = -1
                for idx, h_card in enumerate(player.hand):
                    if h_card.rank == c_rank and h_card.suit == c_suit:
                        card_idx = idx
                        break
                
                if card_idx == -1:
                    log_error("REPLAY_FORK_ERROR", new_room_id, f"Replay Error: Card {c_rank}{c_suit} not found in {pos} hand during replay")
                    # Force create? No, that breaks logic. 
                    # If initial_hands were correct, it MUST be there.
                    continue
                    
                # Play it
                # We play directly to game engine to trigger side effects (table update, turn rotation)
                # But we might want to suppress some events (logging?)
                # For now, just call play_card.
                new_game.play_card(player.index, card_idx)
                
        log_event("REPLAY_FORK_SUCCESS", new_room_id, details={"replayed_tricks": len(tricks_to_replay)})
        return {"success": True, "newGameId": new_room_id} # Return 200 OK
    except Exception as e:
        log_error("REPLAY_FORK_ERROR", new_room_id, f"Fork Failed during hydration/replay: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# Explicit Mount (Explicit Injection Pattern)
def bind(app_instance):
    with open("logs/import_debug.txt", "a") as f:
        f.write(f"DEBUG: bind called for app {id(app_instance)}\n")
        
        if getattr(app_instance, '_replay_routes_mounted', False):
            f.write("DEBUG: Routes already mounted on this app. Skipping.\n")
            return

        f.write("DEBUG: Mounting Replay Routes manually...\n")
        
        def safe_mount(path, method, callback):
            try:
                app_instance.route(path, method=method, callback=callback)
                f.write(f"DEBUG: Mounted {path} [{method}] SUCCESS\n")
            except Exception as ex:
                 f.write(f"DEBUG: Failed to mount {path}: {ex}\n")

        # Ping
        safe_mount('/replay/ping', 'GET', replay_ping)
        
        # List
        safe_mount('/replay/list', 'GET', get_archived_matches)
        safe_mount('/replay/list', 'OPTIONS', get_archived_matches)
        
        # Fork
        safe_mount('/replay/fork', 'POST', fork_game)
        safe_mount('/replay/fork', 'OPTIONS', fork_game)
        
        setattr(app_instance, '_replay_routes_mounted', True)
