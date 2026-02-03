import socketio
from server.room_manager import room_manager
from ai_worker.personality import PROFILES, BALANCED, AGGRESSIVE, CONSERVATIVE
from ai_worker.agent import bot_agent
from ai_worker.dialogue_system import DialogueSystem
from ai_worker.professor import professor
from ai_worker.memory_hall import memory_hall
import time
import logging

# Configure Logging
# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/server_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import Orchestrator
import server.bot_orchestrator as bot_orchestrator

print(f"DEBUG: Loading socket_handler.py as {__name__} | ID: {id(bot_orchestrator)}")

# Create a Socket.IO server
# async_mode='gevent' is recommended for pywsgi
sio = socketio.Server(async_mode='gevent', cors_allowed_origins='*')
import server.auth_utils as auth_utils
from server.schemas.game import GameStateModel
from server.rate_limiter import limiter

def broadcast_game_update(game, room_id):
    """Helper to emit validated game state with fallback"""
    bot_orchestrator.broadcast_game_update(sio, game, room_id)


# Memory Storage for Authenticated Users (Handshake Auth)
# sid -> {user_id, email, username, ...}
connected_users = {}

dialogue_system = DialogueSystem()

@sio.event
def connect(sid, environ, auth=None):
    # Support both auth dict and query params (for some clients)
    token = (auth or {}).get('token')
    
    # Also check query string as fallback
    if not token:
        from urllib.parse import parse_qs
        qs = environ.get('QUERY_STRING', '')
        params = parse_qs(qs)
        if 'token' in params:
            token = params['token'][0]

    if not token:
        # Reject connection? Or allow Guests?
        # For now, we allow guests but log it. 
        # Ideal architecture: Reject or mark as Guest.
        print(f"Client connected (Guest): {sid}")
        return True # Accepted as Guest
        
    user_data = auth_utils.verify_token(token)
    if not user_data:
        print(f"Invalid Token for SID: {sid}")
        return False # Reject connection
        
    # Success! Store in memory for instant access
    connected_users[sid] = user_data
    print(f"Authorized {user_data.get('email')} (SID: {sid})")
    return True

@sio.event
def disconnect(sid):
    print(f"Client disconnected: {sid}")
    # Cleanup auth memory
    if sid in connected_users:
        del connected_users[sid]
    # TODO: Handle player disconnection from game (auto-play or pause)

@sio.event
def create_room(sid, data):
    print(f"create_room called by {sid}")
    
    # Rate Limit: 5 per minute per SID (or IP if available)
    if not limiter.check_limit(f"create_room:{sid}", 5, 60):
        return {'success': False, 'error': 'Rate limit exceeded. Please wait.'}

    room_id = room_manager.create_room()
    return {'success': True, 'roomId': room_id}

@sio.event
def join_room(sid, data):
    room_id = data.get('roomId')
    player_name = data.get('playerName', 'Guest')
    
    game = room_manager.get_game(room_id)
    if not game:
        return {'success': False, 'error': 'Room not found'}
    
    # Check if already joined? (Simplified: Just add)
    # RESERVED SEAT LOGIC (For Replay Forks)
    reserved = next((p for p in game.players if p.id == "RESERVED_FOR_USER"), None)
    if reserved:
         logger.info(f"User {sid} claiming RESERVED seat in room {room_id}")
         reserved.id = sid
         reserved.name = player_name
         # Update avatar if needed? keep original?
         player = reserved
    else:
        player = game.add_player(sid, player_name)
        
    if not player:
        return {'success': False, 'error': 'Room full'}

    # CRITICAL FIX: If a human joins, ensure they are NOT marked as a bot
    # This recovers the seat if it was previously occupied by a bot or persisted as such
    if player.is_bot:
         logger.warning(f"User {sid} reclaiming Bot Seat {player.index} ({player.name})")
         player.is_bot = False
         player.id = sid # Update SID in case it differed
         room_manager.save_game(game)

    sio.enter_room(sid, room_id)
    
    # For testing: Auto-add 3 bots when first player joins
    if len(game.players) == 1:
        # Define Bot Order
        bot_personas = [BALANCED, AGGRESSIVE, CONSERVATIVE]
        
        for i, persona in enumerate(bot_personas):
            bot_id = f"BOT_{i}_{int(time.time()*1000)}"
            # Use name from persona, append (Bot) for clarity if needed, or keep clean
            display_name = f"{persona.name} (Bot)"
            
            # Add player with avatar
            bot_player = game.add_player(bot_id, display_name, avatar=persona.avatar_id)
            if bot_player:
                bot_player.is_bot = True
                sio.emit('player_joined', {'player': bot_player.to_dict()}, room=room_id)
    
    # Broadcast to room
    sio.emit('player_joined', {'player': player.to_dict()}, room=room_id, skip_sid=sid)
    
    
    if len(game.players) == 4:
         if game.start_game():
             sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
             # Check if first player is bot
             handle_bot_turn(game, room_id)

    # Return game state (Must be AFTER start_game to get correct Dealer/Phase)
    # SAVE GAME STATE (Persist Player Join)
    room_manager.save_game(game)

    response = {
        'success': True,
        'gameState': game.get_game_state(),
        'yourIndex': player.index
    }
             
    return response

@sio.event
def game_action(sid, data):
    room_id = data.get('roomId')
    action = data.get('action')
    payload = data.get('payload', {})
    
    game = room_manager.get_game(room_id)
    if not game:
        return {'success': False, 'error': 'Game not found'}
    
    # Rate Limit: 20 per second per SID (Generous for gameplay, blocks flooding)
    if not limiter.check_limit(f"game_action:{sid}", 20, 1):
        return {'success': False, 'error': 'Too many actions'}
    
    # Map actions
    # Find player index
    player = next((p for p in game.players if p.id == sid), None)
    if not player:
        return {'success': False, 'error': 'Player not in this game'}
        
    result = {'success': False}
    if action == 'BID':
        result = game.handle_bid(player.index, payload.get('action'), payload.get('suit'))
    if action.startswith('QAYD'):
        print(f"[SOCKET] QAYD ACTION RECEIVED: {action} from {player.name} ({player.index})")
        logger.info(f"[SOCKET] QAYD ACTION RECEIVED: {action}")

    if action == 'PLAY':
        # CHECK FOR PROFESSOR INTERVENTION (If Human Player)
        # Skip if explicitly bypassed (user clicked "I know what I'm doing")
        skip_professor = payload.get('skip_professor', False)
        
        intervention = None
        if not skip_professor and not player.is_bot:
             card_idx = payload.get('cardIndex')
             intervention = professor.check_move(game, player.index, card_idx)
             
        if intervention:
             result = {'success': False, 'error': 'PROFESSOR_INTERVENTION', 'intervention': intervention}
             game.pause_timer()
             game.increment_blunder(player.index)
             # Must save state because pause_timer / increment_blunder modified it
             room_manager.save_game(game) 
        else:
            metadata = payload.get('metadata', {})
            # Inject cardId into metadata for robust validation
            if 'cardId' in payload:
                metadata['cardId'] = payload['cardId']
                
            result = game.play_card(player.index, payload.get('cardIndex'), metadata=metadata)
    elif action == 'DECLARE_PROJECT':
        result = game.handle_declare_project(player.index, payload.get('type'))
    elif action == 'DOUBLE':
        result = game.handle_double(player.index)
    elif action == 'SAWA' or action == 'SAWA_CLAIM':
        # Result of Sawa request
        if hasattr(game, 'handle_sawa'):
             result = game.handle_sawa(player.index)
        else:
             result = {'success': False, 'error': 'Sawa not implemented backend'}
    elif action == 'SAWA_RESPONSE':
        if hasattr(game, 'handle_sawa_response'):
             result = game.handle_sawa_response(player.index, payload.get('response')) # ACCEPT/REFUSE
        else:
             result = {'success': False, 'error': 'Sawa Response not implemented'}

    elif action == 'QAYD':
         # Legacy Qayd (Simple Claim) - Deprecated or used for simple reporting
         result = game.handle_qayd(player.index, payload.get('reason'))
    
    # --- FORENSIC (VAR) ACTIONS ---
    elif action == 'QAYD_TRIGGER':
         result = game.handle_qayd_trigger(player.index)
         
    elif action == 'QAYD_ACCUSATION':
         result = game.handle_qayd_accusation(player.index, payload.get('accusation'))
    elif action == 'QAYD_CONFIRM':
         result = game.handle_qayd_confirm()
    elif action == 'QAYD_CANCEL':
         result = game.handle_qayd_cancel()
    elif action == 'AKKA':
        result = game.handle_akka(player.index)
    elif action == 'UPDATE_SETTINGS':
        # New Action to sync settings
        if 'turnDuration' in payload:
             game.turn_duration = float(payload['turnDuration'])
             logger.info(f"Updated Turn Duration to {game.turn_duration}s for room {room_id}")
        result = {'success': True}
    elif action == 'NEXT_ROUND':
        if game.phase == "FINISHED":
             logger.info(f"Starting Next Round for room {room_id} by request.")
             if game.start_game():
                 sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                 handle_bot_turn(game, room_id)
             result = {'success': True}
        elif game.phase == "GAMEOVER":
             logger.info(f"Starting New Match (Rematch) for room {room_id} by request.")
             # Reset Match Scores
             game.match_scores = {'us': 0, 'them': 0}
             game.past_round_results = []
             game.full_match_history = []
             
             if game.start_game():
                 sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                 handle_bot_turn(game, room_id)
             result = {'success': True}
             room_manager.save_game(game) # Save new match state
        else:
             result = {'success': False, 'error': 'Cannot start round, phase is ' + game.phase}
    
    if result.get('success'):
        # PERSIST STATE TO REDIS
        room_manager.save_game(game)
        
        # Broadcast Update
        broadcast_game_update(game, room_id)
        
        # Trigger Bot Responses for Sawa
        if action == 'SAWA' or action == 'SAWA_CLAIM':
             sio.start_background_task(bot_orchestrator.handle_sawa_responses, sio, game, room_id)
        
        # --- SHERLOCK WATCHDOG --- 
        sio.start_background_task(bot_orchestrator.run_sherlock_scan, sio, game, room_id)
        # -------------------------

        # Trigger Bot Loop (Background)
        st = game.get_game_state()
        cur_turn_export = st['currentTurnIndex']
        # with open('logs/server_manual.log', 'a') as f:
        #      f.write(f"{time.time()} Game Action Success. Turn: {game.current_turn} Exported: {cur_turn_export} ID: {id(game)}\n")
        try:
             sio.start_background_task(bot_orchestrator.bot_loop, sio, game, room_id)
        except Exception as e:
             logger.error(f"Failed to start bot task: {e}")
        
        # Check if game finished to trigger auto-restart
        if game.phase == "FINISHED":
             save_match_snapshot(game, room_id)
             # Auto-restart logic is handled by client request or explicit timer
             pass
        
    return result

# run_sherlock_scan moved to bot_orchestrator

@sio.event
def client_log(sid, data):
    """Receive telemetry logs from client"""
    try:
        category = data.get('category', 'CLIENT')
        level = data.get('level', 'INFO')
        msg = data.get('message', '')
        
        log_line = f"[{level}] [{category}] {msg}"
        print(f"[CLIENT-LOG] {log_line}")
        
        # Write to file for Agent to read
        with open('logs/client_debug.log', 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {log_line}\n")
            
    except Exception as e:
        print(f"Error logging client message: {e}")

# bot_loop moved to bot_orchestrator

# handle_sawa_responses moved to bot_orchestrator

def save_match_snapshot(game, room_id):
    """Helper to save match state to DB on round completion"""
    
    # DEBUG: Force log to file
    def debug_log(msg):
        try:
            with open("logs/archive_debug.txt", "a") as f:
                import datetime
                f.write(f"{datetime.datetime.now()} - {msg}\n")
        except: pass

    try:
        debug_log(f"Attempting to save snapshot for room {room_id}")
        import json
        from server.common import db
        # Ensure imports
        
        human = next((p for p in game.players if not p.is_bot), None)
        history_json = json.dumps(game.full_match_history, default=str)
        debug_log(f"History Length: {len(game.full_match_history)}")
        
        # Check if table exists (lazy check)
        if not hasattr(db, 'match_archive'):
             logger.error("DB match_archive table missing. Cannot save.")
             debug_log("ERROR: match_archive missing from db object")
             debug_log(f"DB Tables: {getattr(db, 'tables', 'UNKNOWN')}")
             return

        db.match_archive.update_or_insert(
            db.match_archive.game_id == room_id,
            game_id=room_id,
            user_email=human.id if human else 'bot_only',
            history_json=history_json,
            final_score_us=game.match_scores['us'],
            final_score_them=game.match_scores['them']
        )
        db.commit()
        logger.info(f"Match {room_id} snapshot archived to DB.")
        debug_log("SUCCESS: Saved to DB")
    except Exception as e:
        logger.error(f"Snapshot Archive Failed: {e}")
        debug_log(f"EXCEPTION: {e}")
        import traceback
        debug_log(traceback.format_exc())

def handle_bot_turn(game, room_id):
    # Wrapper
    sio.start_background_task(bot_orchestrator.bot_loop, sio, game, room_id, 0)

def auto_restart_round(game, room_id):
    """Wait for 3 seconds then start next round if match is not over"""
    try:
        # race condition guard
        if hasattr(game, 'is_restarting') and game.is_restarting:
            return

        game.is_restarting = True
        sio.sleep(3.0) # Wait 3 seconds for score display

        # HELPER: Save to Archive
        def save_to_archive():
            try:
                import json
                from server.common import db
                human = next((p for p in game.players if not p.is_bot), None)
                history_json = json.dumps(game.full_match_history, default=str)
                db.match_archive.update_or_insert(
                    db.match_archive.game_id == room_id,
                    game_id=room_id,
                    user_email=human.id if human else 'bot_only',
                    history_json=history_json,
                    final_score_us=game.match_scores['us'],
                    final_score_them=game.match_scores['them']
                )
                db.commit()
                logger.info(f"Match {room_id} archived to DB successfully (Round End).")
            except Exception as db_err:
                logger.error(f"Failed to archive match to DB: {db_err}")

        print(f"Checking auto-restart for room {room_id}. Phase: {game.phase}")
        
        if game.phase == "FINISHED":
             print(f"Auto-restarting round for room {room_id}. Current scores: US={game.match_scores['us']}, THEM={game.match_scores['them']}")
             
             # Save Progress
             save_to_archive()

             if game.start_game():
                  game.is_restarting = False # Reset flag
                  sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                  handle_bot_turn(game, room_id)
        elif game.phase == "GAMEOVER":
             game.is_restarting = False
             print(f"Match FINISHED for room {room_id} (152+ reached). Final score: US={game.match_scores['us']}, THEM={game.match_scores['them']}")
             
             # Save Final
             save_to_archive()

             # PERSIST LEGACY: Remember the match
             try:
                 human = next((p for p in game.players if not p.is_bot), None)
                 if human:
                     # Determine Winner
                     us_score = game.match_scores['us']
                     them_score = game.match_scores['them']
                     
                     winner_team = 'us' if us_score >= 152 else 'them'
                     if human.index in [0, 2]:
                         player_won = (winner_team == 'us')
                     else:
                         player_won = (winner_team == 'them')
                         
                     # Identify Partner & Opponents
                     partner_idx = (human.index + 2) % 4
                     opp1_idx = (human.index + 1) % 4
                     opp2_idx = (human.index + 3) % 4
                     
                     match_data = {
                         'winner': 'us' if player_won else 'them',
                         'my_partner': game.players[partner_idx].name,
                         'opponents': [game.players[opp1_idx].name, game.players[opp2_idx].name],
                         'score_us': us_score if human.index in [0, 2] else them_score, # 'us' from player perspective
                         'score_them': them_score if human.index in [0, 2] else us_score
                     }
                     
                     memory_hall.remember_match(human.id, human.name, match_data)
             except Exception as mem_err:
                 logger.error(f"Failed to save memory: {mem_err}")

        else:
             game.is_restarting = False
             
    except Exception as e:
        logger.error(f"Error in auto_restart_round: {e}")
        if game: game.is_restarting = False

@sio.event
def add_bot(sid, data):
    room_id = data.get('roomId')
    if not room_id or room_id not in room_manager.games:
        return {'success': False, 'error': 'Room not found'}
        
    game = room_manager.games[room_id]
    
    # Cycle through personas: Balanced -> Aggressive -> Conservative
    personas = [BALANCED, AGGRESSIVE, CONSERVATIVE]
    persona = personas[len(game.players) % 3]
    
    name = f"{persona.name} (Bot)"
    
    bot_id = f"BOT_{len(game.players)}_{int(time.time())}"
    player = game.add_player(bot_id, name, avatar=persona.avatar_id)
    
    if not player:
        return {'success': False, 'error': 'Room full'}
        
    player.is_bot = True 
    room_manager.save_game(game) # Persist Bot Join
    
    sio.emit('player_joined', {'player': player.to_dict()}, room=room_id)
    
    if len(game.players) == 4:
         if game.start_game():
             sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
             # Check if first player is bot
             handle_bot_turn(game, room_id)
             
    return {'success': True}

# Check game start logic (usually called after join)
@sio.event
def check_start(sid, data):
    room_id = data.get('roomId')
    game = room_manager.get_game(room_id)
    if game and len(game.players) == 4:
         if game.start_game():
             room_manager.save_game(game) # Persist Game Start
             sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
             handle_bot_turn(game, room_id)

TIMER_TASK_STARTED = False

def timer_background_task(room_manager_instance):
    """Background task to check for timeouts in all active games"""
    global TIMER_TASK_STARTED
    import os, threading, sys
    debug_msg = f"PID: {os.getpid()} | Thread: {threading.get_ident()} | Module: {__name__} | Flag Addr: {id(TIMER_TASK_STARTED)} | Value: {TIMER_TASK_STARTED}\n"
    
    # Check for duplicate modules
    sock_modules = [k for k in sys.modules.keys() if 'socket_handler' in k]
    debug_msg += f"Loaded Socket Handlers: {sock_modules}\n"
    
    with open("logs/singleton_debug.log", "a") as f:
        f.write(f"{time.time()} PRE-CHECK: {debug_msg}")

    if TIMER_TASK_STARTED:
        logger.warning(f"Timer Background Task ALREADY RUNNING. Skipping. {debug_msg}")
        with open("logs/singleton_debug.log", "a") as f:
            f.write(f"{time.time()} SKIPPED: {debug_msg}")
        return

    TIMER_TASK_STARTED = True
    
    with open("logs/singleton_debug.log", "a") as f:
        f.write(f"{time.time()} STARTED: {debug_msg}")

    last_heartbeat = time.time()
    logger.info("Timer Background Task Started")
    
    # Dedicated Debug Logger
    with open("logs/timer_monitor.log", "w") as f:
        f.write(f"{time.time()} STARTUP\n")

    while True:
        sio.sleep(0.1) # Check every 0.1 second for smoother timeouts
        
        now = time.time()
        if now - last_heartbeat > 10:
             logger.info(f"Timer Task Heartbeat. Checking {len(room_manager_instance.games)} games.")
             with open("logs/timer_monitor.log", "a") as f:
                  f.write(f"{now} HEARTBEAT {len(room_manager_instance.games)} games\n")
             last_heartbeat = now
             
        try:
            # Create list of IDs to iterate safely (in case dict changes size)
            room_ids = list(room_manager_instance.games.keys())
            
            for room_id in room_ids:
                game = room_manager_instance.get_game(room_id)
                if not game: continue
                
                res = game.check_timeout()
                if res and res.get('success'):
                    # Timeout caused an action (Pass or AutoPlay)
                    # Broadcast update
                    room_manager.save_game(game) # Persist Timeout Action
                    broadcast_game_update(game, room_id)
                    
                    # Trigger Bot if next player is bot
                    # (Standard bot_loop handles logic, we just trigger it)
                    handle_bot_turn(game, room_id)
                    
                    # Check finish
                    if game.phase == "FINISHED":
                         save_match_snapshot(game, room_id)
                         # sio.start_background_task(auto_restart_round, game, room_id)
                         pass

        except Exception as e:
            logger.error(f"Error in timer_background_task: {e}")
            sio.sleep(5.0) # Backoff on error

def handle_bot_speak(game, room_id, player, action, result):
    """Generate and emit bot dialogue"""
    try:
        # Determine Personality from Avatar or Name
        # Defaults to BALANCED
        personality = BALANCED 
        # Reverse map avatar/name
        # Simple heuristic based on avatar string we assigned
        if "khalid" in player.avatar: personality = AGGRESSIVE
        elif "abu_fahad" in player.avatar: personality = CONSERVATIVE
        elif "saad" in player.avatar: personality = BALANCED

        # Construct Context
        # "I bid SUN." "I played Ace of Spades."
        context = f"Did action: {action}."
        if action == 'AKKA':
             context += " I declared Akka (Highest Non-Trump). I command this suit!"
        
        # Add Game Context
        if game.last_trick and action == 'PLAY':
             winner = game.last_trick.get('winner') if isinstance(game.last_trick, dict) else getattr(game.last_trick, 'winner', None)
             if winner == player.position:
                 context += " I won this trick."
        
        if game.phase == "BIDDING":
             bid_type = game.bid.get('type') if isinstance(game.bid, dict) else getattr(game.bid, 'type', 'None')
             context += f" Current Bid: {bid_type or 'None'}."

        # Fetch Rivalry Context (Human Player)
        human = next((p for p in game.players if not p.is_bot), None)
        rivalry_summary = {}
        if human:
             rivalry_summary = memory_hall.get_rivalry_summary(human.id)

        # Generate
        text = dialogue_system.generate_reaction(player.name, personality, context, game_state=None, rivalry_summary=rivalry_summary)
        
        if text:
            sio.emit('bot_speak', {
                'playerIndex': player.index,
                'text': text,
                'emotion': 'neutral'
            }, room=room_id)
            
    except Exception as e:
        logger.error(f"Error in handle_bot_speak: {e}")
