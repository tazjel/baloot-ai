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




# MULTIVERSE TREE (Genealogy)
@action('replay/multiverse', method=['GET', 'OPTIONS'])
@action.uses(db)
def get_multiverse_tree():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Content-Type'] = 'application/json'

    if request.method == 'OPTIONS':
        return ""

    try:
        # 1. Fetch all games (limit 100 for performance)
        rows = db(db.match_archive).select(
            db.match_archive.game_id,
            db.match_archive.final_score_us,
            db.match_archive.final_score_them,
            db.match_archive.timestamp,
            orderby=~db.match_archive.timestamp,
            limitby=(0, 100)
        )

        nodes = []
        seen_ids = set()
        
        # Helper to process node
        def process_node(gid, score_us, score_them, ts, is_active=False):
            if gid in seen_ids: return
            seen_ids.add(gid)
            
            parent_id = None
            if gid.startswith('replay_'):
                parts = gid.split('_')
                if len(parts) >= 6:
                    suffix_len = 4
                    parent_parts = parts[1:-suffix_len]
                    parent_id = "_".join(parent_parts)

            nodes.append({
                "id": gid,
                "parentId": parent_id,
                "scoreUs": score_us,
                "scoreThem": score_them,
                "timestamp": str(ts),
                "isFork": bool(parent_id),
                "isActive": is_active
            })

        # A. Archived Games
        for r in rows:
            process_node(r.game_id, r.final_score_us, r.final_score_them, r.timestamp)
            
        # B. Active Games (In-Memory)
        try:
            # Use .games property which aggregates Redis/Local
            current_games = room_manager.games
            
            for gid, game in current_games.items():
                if gid.startswith('replay_'):
                     # Calculate ephemeral score
                     s_us = game.match_scores.get('us', 0)
                     s_them = game.match_scores.get('them', 0)
                     # active games fallback to created_at if timestamp missing
                     ts = getattr(game, 'created_at', '0')
                     process_node(gid, s_us, s_them, ts, is_active=True)
                     
        except Exception as active_err:
            logger.warning(f"Multiverse: Failed to fetch active games: {active_err}")

        return json.dumps({"nodes": nodes})

    except Exception as e:
        log_error("MULTIVERSE_ERROR", "GLOBAL", str(e))
        return json.dumps({"error": str(e), "nodes": []})


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
    moves_in_trick = data.get('movesInTrick', 0) # Number of moves to play in the PARTIAL trick

    log_event("REPLAY_FORK_REQUEST", str(source_game_id), details={"round": round_num, "trick": trick_index, "moves": moves_in_trick})

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
    new_room_id = f"replay_{source_game_id}_{round_num}_{trick_index}_{moves_in_trick}_{uuid.uuid4().hex[:8]}"
    log_event("REPLAY_FORK_START", new_room_id, details={"source": source_game_id, "source_type": source_type, "round": round_num, "trick": trick_index})
    
    new_game = Game(new_room_id)
    
    # Time Lord / Ghost Metadata
    # We want to know:
    # 1. source_game_id
    # 2. current_score_us (at moment of fork) -> To compare later? 
    #    Actually better: We track 'forked_at_score_diff'.
    #    But simplest: Store 'original_game_id'. Frontend can fetch original game details?
    #    No, frontend wants "Ghost: +12".
    #    So we need 'source_score_us' and 'source_score_them' AT THE END OF THIS GAME (Final).
    #    If the game isn't finished, we can't show "Ghost of Past".
    #    Wait, "Ghost of Past" implies comparing to what YOU did before.
    #    If you replay a finished game, we know the final score.
    #    Let's store 'original_final_scores' in metadata.
    
    original_final_scores = None
    if source_game:
        # If active game, maybe not final?
        pass 
    elif record:
        # From DB
        original_final_scores = {"us": record.final_score_us, "them": record.final_score_them}

    new_game.metadata = {
        "source_game_id": source_game_id,
        "forked_at_round": round_num,
        "forked_at_trick": trick_index,
        "original_final_scores": original_final_scores
    }

    room_manager.save_game(new_game)
    
    # 3. Hydrate State
    try:
        # A. Basic Setup
        new_game.players = [] # Reset default players if any
        
        # 0. Add You
        new_game.add_player("RESERVED_FOR_USER", "You (Forked)")
        
        # 1. Add Others (Indices 1, 2, 3)
        if source_game:
             for i, p in enumerate(source_game.players):
                 if i == 0: continue # Skip original Bottom, we took it
                 bot_id = f"BOT_FORK_{i}_{uuid.uuid4().hex[:4]}"
                 bot_player = new_game.add_player(bot_id, f"{p.name} (Bot)", p.avatar)
                 if bot_player: bot_player.is_bot = True
        else:
             for i in range(1, 4):
                 bot_id = f"BOT_FORK_{i}_{uuid.uuid4().hex[:4]}"
                 bot_player = new_game.add_player(bot_id, f"Player {i} (Bot)")
                 if bot_player: bot_player.is_bot = True

        # B. Match State
        # Minimal Logic for MVP - Recalculate match scores from previous rounds? 
        # Or just trust snapshot if available?
        # Let's assume snapshot doesn't have match_scores yet, so default to 0 for now.
        # This will be fixed in v2.
        
        # C. Round State
        new_game.dealer_index = snapshot['dealerIndex']
        new_game.floor_card = None 
        new_game.bid = snapshot['bid']
        new_game.game_mode = new_game.bid['type']
        new_game.trump_suit = new_game.bid['suit']
        new_game.doubling_level = 2 if new_game.bid['doubled'] else 1
        
        new_game.phase = GamePhase.PLAYING.value
        
        # D. Restore Hands
        initial_hands = snapshot.get('initialHands')
        if not initial_hands:
             log_error("REPLAY_FORK_ERROR", new_room_id, "Snapshot missing initialHands data")
             return {"error": "Snapshot missing initialHands data (Cannot Replay)"}
        
        pos_map = {p.position: p for p in new_game.players}
        
        for pos, cards_data in initial_hands.items():
            if pos in pos_map:
                player = pos_map[pos]
                player.hand = [Card(c['suit'], c['rank']) for c in cards_data]

        # E. Replay Moves
        
        # FIX: Persist initial_hands so this forked game can itself be forked (Nested Replays)
        new_game.initial_hands = initial_hands

        from game_engine.logic.bidding_engine import BiddingEngine
        be = BiddingEngine(new_game.dealer_index, new_game.floor_card, new_game.players, new_game.match_scores)
        be.contract = DummyContract(new_game.bid)
        new_game.bidding_engine = be

        target_trick_count = int(trick_index)
        all_tricks = snapshot['tricks']
        
        # FULL Replay of previous tricks
        tricks_to_replay = all_tricks[:target_trick_count]
        
        new_game.current_turn = (new_game.dealer_index + 1) % 4
        
        def replay_move(card_data, pos):
             player = pos_map[pos]
             c_rank = card_data['rank']
             c_suit = card_data['suit']
             
             card_idx = -1
             for idx, h_card in enumerate(player.hand):
                 if h_card.rank == c_rank and h_card.suit == c_suit:
                     card_idx = idx
                     break
             
             if card_idx == -1:
                 logger.warning(f"Replay Warning: Card {c_rank}{c_suit} not found in {pos} hand")
                 return
                 
             new_game.play_card(player.index, card_idx)

        # 1. Full Tricks
        for trick in tricks_to_replay:
            cards = trick['cards']
            played_bys = trick.get('playedBy', [])
            for i, card_data in enumerate(cards):
                replay_move(card_data, played_bys[i])

        # 2. Partial Trick (The "Time Lord" moment)
        if moves_in_trick > 0 and target_trick_count < len(all_tricks):
             current_trick = all_tricks[target_trick_count]
             partial_cards = current_trick['cards'][:moves_in_trick]
             partial_players = current_trick.get('playedBy', [])[:moves_in_trick]
             
             logger.info(f"Replaying PARTIAL trick {target_trick_count}: {len(partial_cards)} moves")
             
             for i, card_data in enumerate(partial_cards):
                  replay_move(card_data, partial_players[i])

        log_event("REPLAY_FORK_SUCCESS", new_room_id, details={"replayed_tricks": len(tricks_to_replay), "partial_moves": moves_in_trick})
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
        
        # Multiverse
        safe_mount('/replay/multiverse', 'GET', get_multiverse_tree)
        safe_mount('/replay/multiverse', 'OPTIONS', get_multiverse_tree)
        
        setattr(app_instance, '_replay_routes_mounted', True)
