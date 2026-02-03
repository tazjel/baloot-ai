
import time
import logging
from ai_worker.agent import bot_agent
from ai_worker.personality import BALANCED, AGGRESSIVE, CONSERVATIVE
from server.schemas.game import GameStateModel
from server.room_manager import room_manager # Needed for persistence

logger = logging.getLogger(__name__)

def broadcast_game_update(sio, game, room_id):
    """Helper to emit validated game state with fallback"""
    import json
    try:
        from server.schemas.game import GameStateModel
        
        # Get game state
        state = game.get_game_state()
        
        # Validate JSON serializability BEFORE schema validation
        try:
            json.dumps(state)
        except TypeError as json_err:
            logger.error(f"[BROADCAST] State not JSON-serializable: {json_err}")
            logger.error(f"[BROADCAST] Problematic state keys: {list(state.keys())}")
            raise
        
        # Validate with schema
        state_model = GameStateModel(**state)
        sio.emit('game_update', {'gameState': state_model.model_dump(mode='json', by_alias=True)}, room=room_id)
        
    except Exception as e:
        logger.critical(f"SCHEMA VALIDATION FAILED for Room {room_id}: {e}")
        logger.error(f"[BROADCAST] Error type: {type(e).__name__}")
        
        # Fallback: try to send raw state (may still fail if not serializable)
        try:
            sio.emit('game_update', {'gameState': game.get_game_state()}, room=room_id)
            logger.warning(f"[BROADCAST] Fallback succeeded for room {room_id}")
        except Exception as fallback_err:
            logger.critical(f"[BROADCAST] Fallback also failed: {fallback_err}")
            # Send minimal error state as last resort
            sio.emit('game_update', {
                'error': 'State serialization failed',
                'phase': game.phase,
                'room_id': room_id
            }, room=room_id)

def handle_bot_speak(sio, game, room_id, player, action, result):
    """Generate and emit bot dialogue"""
    try:
        # Determine Personality
        personality = BALANCED 
        if "khalid" in player.avatar: personality = AGGRESSIVE
        elif "abu_fahad" in player.avatar: personality = CONSERVATIVE
        elif "saad" in player.avatar: personality = BALANCED

        context = f"Did action: {action}."
        if action == 'AKKA':
             context += " I declared Akka (Highest Non-Trump). I command this suit!"
        
        # Trigger Voice/Chat via SIO or DialogueSystem (omitted for brevity/refactor scope)
        # Keeping existing logic if it was simple or delegate
    except Exception as e:
        logger.error(f"Bot Speak Error: {e}")

def run_sherlock_scan(sio, game, room_id):
    """
    Independent Watchdog process.
    Allows ALL bots to check for illegal moves immediately after ANY action.
    """
    try:
        if game.phase != "PLAYING" or game.qayd_manager.state.get('active'):
            return

        state = game.get_game_state()
        
        for player in game.players:
            if player.is_bot:
                decision = bot_agent.get_decision(state, player.index)
                if decision.get('action') == 'QAYD_ACCUSATION':
                    logger.warning(f"[WATCHDOG] Bot {player.name} detected PROVEN crime! INTERRUPTING.")
                    
                    # Extract crime data from bot's decision
                    crime_data = decision.get('crime', {})
                    accusation = {
                        'crime_card': crime_data.get('crime_card'),
                        'proof_card': crime_data.get('proof_card'),
                        'qayd_type': decision.get('qayd_type', 'REVOKE'),
                        'crime_trick_idx': crime_data.get('crime_trick_idx'),
                        'proof_trick_idx': crime_data.get('proof_trick_idx'),
                        'offender': crime_data.get('player')  # The cheater's position
                    }
                    
                    res = game.handle_qayd_accusation(player.index, accusation)
                    if res.get('success'):
                        logger.info(f"Bot {player.name} successfully triggered Qayd with proof via Watchdog.")
                        broadcast_game_update(sio, game, room_id)
                        return
                elif decision.get('action') == 'QAYD_TRIGGER':
                    # Legacy trigger without explicit proof
                    logger.warning(f"[WATCHDOG] Bot {player.name} triggered Qayd (legacy). INTERRUPTING.")
                    res = game.handle_qayd_trigger(player.index)
                    if res.get('success'):
                        logger.info(f"Bot {player.name} successfully triggered Qayd via Watchdog.")
                        broadcast_game_update(sio, game, room_id)
                        return
    except Exception as e:
        logger.error(f"Sherlock Watchdog Error: {e}")

def handle_sawa_responses(sio, game, room_id):
    """Trigger all bots to respond to a Sawa claim"""
    logger.info(f"Starting Sawa Responses for Room {room_id}")
    try:
        sio.sleep(0.5)
        
        if not game.sawa_state['active']: 
             return

        for p in game.players:
            if p.is_bot:
                decision = bot_agent.get_decision(game.get_game_state(), p.index)
                
                if decision and decision.get('action') == 'SAWA_RESPONSE':
                    resp = decision.get('response')
                    res = game.handle_sawa_response(p.index, resp)
                    if res.get('success'):
                         broadcast_game_update(sio, game, room_id)
                         room_manager.save_game(game)
                         
                         if res.get('sawa_status') == 'REFUSED':
                              break
    except Exception as e:
        logger.error(f"Error in handle_sawa_responses: {e}")


def bot_loop(sio, game, room_id, recursion_depth=0):
    """Background task to handle consecutive bot turns"""
    try:
        if recursion_depth > 500:
             logger.warning(f"Bot Loop Safety Break (Depth {recursion_depth})")
             return
        
        if not game or not game.players: return
            
        if game.phase not in ["BIDDING", "PLAYING", "DOUBLING", "VARIANT_SELECTION"]:
            return
        
        if game.current_turn < 0 or game.current_turn >= len(game.players): return
        
        # 1. Respect Qayd State (Stop if investigation active)
        if game.qayd_manager.state.get('active'):
            return

        next_idx = game.current_turn
        if not game.players[next_idx].is_bot:
            broadcast_game_update(sio, game, room_id)
            return

        # 2. Throttle Bot Loop (Prevent Freeze)
        sio.sleep(1.5) 
        
        if game.phase == "FINISHED": return
            
        current_idx = game.current_turn
        current_player = game.players[current_idx]
        
        if not current_player.is_bot: return
            
        decision = bot_agent.get_decision(game.get_game_state(), current_idx)
        
        action = decision.get('action')
        reasoning = decision.get('reasoning')
        res = {'success': False}
        
        if action == 'AKKA':
             res = game.handle_akka(current_idx)

        elif action == 'QAYD_TRIGGER':
             res = game.handle_qayd_trigger(current_idx)

        elif action == 'QAYD_ACCUSATION':
             # Proof-based accusation: extract crime and proof data
             crime_data = decision.get('crime', {})
             accusation_data = decision.get('accusation', {})
             
             # Merge compatible formats (legacy 'accusation' vs new 'crime')
             crime_card = crime_data.get('crime_card') or accusation_data.get('crime_card')
             proof_card = crime_data.get('proof_card') or accusation_data.get('proof_card')
             qayd_type = decision.get('qayd_type', 'REVOKE')
             
             res = game.handle_qayd_accusation(
                 current_idx,
                 {
                     'crime_card': crime_card,
                     'proof_card': proof_card,
                     'qayd_type': qayd_type,
                     'crime_trick_idx': crime_data.get('crime_trick_idx'),
                     'proof_trick_idx': crime_data.get('proof_trick_idx')
                 }
             )

        elif action == 'QAYD_CANCEL':
             res = game.handle_qayd_cancel()

        elif game.phase in ["BIDDING", "DOUBLING", "VARIANT_SELECTION"]:
                action = action.upper() if action else "PASS"
                suit = decision.get('suit')
                res = game.handle_bid(current_idx, action, suit, reasoning=reasoning)
                
        elif game.phase == "PLAYING":
                card_idx = decision.get('cardIndex', 0)
                metadata = {}
                if reasoning: metadata['reasoning'] = reasoning
                if decision.get('declarations'): metadata['declarations'] = decision['declarations']
                res = game.play_card(current_idx, card_idx, metadata=metadata)
        
        if res.get('success'):
             broadcast_game_update(sio, game, room_id)
             
             # 3. Trigger Sherlock (Watchdog) to catch illegal moves IMMEDIATEY
             sio.start_background_task(run_sherlock_scan, sio, game, room_id)

             # sio.start_background_task(handle_bot_speak, sio, game, room_id, current_player, action, res) # Optional

             if game.phase == "FINISHED":
                  room_manager.save_game(game)
                  return
             
             room_manager.save_game(game)
             sio.start_background_task(bot_loop, sio, game, room_id, recursion_depth + 1)
        else:
             logger.error(f"Bot Action Failed: {res}. Attempting Fallback.")
             
             # CRITICAL: Don't attempt fallback if game is locked for Qayd
             if game.is_locked:
                 logger.info("Bot action failed due to Game Lock (Qayd). Skipping fallback.")
                 return
             
             logger.error(f"Bot Action Failed: {res}. Attempting Fallback (Random Play).")
             
             # Fallback: Try playing the first card available
             # This prevents the game from freezing if the AI's complex move was rejected
             try:
                 fallback_res = game.play_card(current_idx, 0, metadata={'reasoning': 'Fallback Random'})
                 if fallback_res.get('success'):
                      broadcast_game_update(sio, game, room_id)
                      room_manager.save_game(game)
                      sio.start_background_task(bot_loop, sio, game, room_id, recursion_depth + 1)
                 else:
                      logger.critical(f"Bot Fallback Failed too: {fallback_res}. Game might be stuck.")
             except Exception as fe:
                 logger.error(f"Fallback Exception: {fe}")
            
    except Exception as e:
        logger.error(f"Critical Bot Loop Error: {e}")
