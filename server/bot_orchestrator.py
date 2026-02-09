
import time
import logging
import os
from ai_worker.agent import bot_agent
from ai_worker.personality import BALANCED, AGGRESSIVE, CONSERVATIVE
from server.schemas.game import GameStateModel
from server.room_manager import room_manager # Needed for persistence

logger = logging.getLogger(__name__)

# ── Bot Speed Configuration ──────────────────────────────────────────────────
# Control via environment variables or change defaults here.
# Set BALOOT_BOT_SPEED=fast for quick testing, or BALOOT_BOT_SPEED=normal for gameplay.
_speed = os.environ.get('BALOOT_BOT_SPEED', 'normal').lower()
BOT_TURN_DELAY   = 0.5 if _speed == 'fast' else 1.5   # Delay between bot actions
QAYD_RESULT_DELAY = 1.0 if _speed == 'fast' else 3.0   # Qayd result display time
SAWA_DELAY        = 0.2 if _speed == 'fast' else 0.5   # Sawa response delay

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

def _sherlock_log(msg):
    """Write debug line to sherlock_debug.log"""
    import datetime
    with open('logs/sherlock_debug.log', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")

def _clear_illegal_flags_on_game(game):
    """
    Clear is_illegal flags on the LIVE game object's table_cards and round_history.
    This prevents re-detection of the same crime through the serialization pathway
    (Bug 3 fix: ForensicScanner clears flags on serialized copies, not the original).
    """
    # Clear on table_cards
    for tc in game.table_cards:
        meta = tc.get('metadata')
        if meta and meta.get('is_illegal'):
            meta['is_illegal'] = False
    # Clear on round_history
    for trick in game.round_history:
        for meta in (trick.get('metadata') or []):
            if meta and meta.get('is_illegal'):
                meta['is_illegal'] = False

def run_sherlock_scan(sio, game, room_id):
    """
    Independent Watchdog process.
    Allows ONE bot to detect an illegal move and trigger Qayd via QaydEngine.
    All penalty logic goes through QaydEngine — NO direct penalty path.
    """
    try:
        _sherlock_log(f"Scan invoked. Phase={game.phase}, Locked={game.is_locked}, Qayd={game.qayd_state.get('active')}")
        # Skip if not in PLAYING or FINISHED phase
        # FINISHED is allowed because the trick may have just resolved (race condition:
        # the illegal card is now in round_history, table_cards is clear, and the round ended)
        if game.phase not in ("PLAYING", "FINISHED"):
            _sherlock_log(f"SKIP: Phase is {game.phase}, not PLAYING/FINISHED")
            return
        # Skip if Qayd already active or recently resolved
        if game.qayd_state.get('active'):
            _sherlock_log(f"SKIP: Qayd already active")
            return
        if game.is_locked:
            _sherlock_log(f"SKIP: Game is locked")
            return

        # GLOBAL LOCK: Prevent race condition between bots
        if hasattr(game, '_sherlock_lock') and game._sherlock_lock:
            _sherlock_log(f"SKIP: Sherlock lock held")
            return
        game._sherlock_lock = True
        
        try:
            state = game.get_game_state()
            
            # Check for illegal cards in table (live game object)
            live_table_illegals = [i for i, tc in enumerate(game.table_cards) if (tc.get('metadata') or {}).get('is_illegal')]
            # Check for illegal cards in round_history (live game object)  
            live_history_illegals = []
            for ti, trick in enumerate(game.round_history):
                for ci, meta in enumerate(trick.get('metadata') or []):
                    if meta and meta.get('is_illegal'):
                        live_history_illegals.append((ti, ci))
            _sherlock_log(f"Live table illegals: {live_table_illegals}, Live history illegals: {live_history_illegals}")
            _sherlock_log(f"Table cards: {len(state.get('tableCards', []))}, Serialized table illegals: {len([tc for tc in state.get('tableCards', []) if (tc.get('metadata') or {}).get('is_illegal')])}")

            
            for player in game.players:
                if not player.is_bot:
                    continue
                    
                # Re-check guards (state may have changed from prior bot)
                if game.phase not in ("PLAYING", "FINISHED") or game.qayd_state.get('active') or game.is_locked:
                    break
                
                decision = bot_agent.get_decision(state, player.index)
                action = decision.get('action')
                _sherlock_log(f"Bot {player.name} decided: {action}")
                
                if action == 'QAYD_TRIGGER':
                    _sherlock_log(f"QAYD_TRIGGER from {player.name}! Calling handle_qayd_trigger({player.index})")
                    _sherlock_log(f"  Pre-trigger state: phase={game.phase}, locked={game.is_locked}, qayd_active={game.qayd_state.get('active')}")
                    res = game.handle_qayd_trigger(player.index)
                    _sherlock_log(f"  Trigger result: {res}")
                    
                    if res.get('success'):
                        # Clear is_illegal flags on the LIVE game object to prevent
                        # future scans from re-detecting the same crime (Bug 3 fix)
                        _clear_illegal_flags_on_game(game)
                        _sherlock_log(f"Qayd triggered OK. Cleared is_illegal flags. Re-querying bot for accusation...")
                        room_manager.save_game(game)
                        broadcast_game_update(sio, game, room_id)
                        
                        # Re-query same bot for accusation data now that Qayd is active
                        state = game.get_game_state()  # Refresh state
                        follow_up = bot_agent.get_decision(state, player.index)
                        _sherlock_log(f"  Follow-up decision: action={follow_up.get('action')}")
                        if follow_up.get('action') == 'QAYD_ACCUSATION':
                            accusation_data = follow_up.get('accusation', {})
                            _sherlock_log(f"  Accusation data: {accusation_data}")
                            acc_res = game.handle_qayd_accusation(player.index, {
                                'crime_card': accusation_data.get('crime_card'),
                                'proof_card': accusation_data.get('proof_card'),
                                'violation_type': accusation_data.get('violation_type', 'REVOKE'),
                            })
                            _sherlock_log(f"  Accusation result: {acc_res}")
                            room_manager.save_game(game)
                            broadcast_game_update(sio, game, room_id)
                            
                            # Auto-confirm after delay (don't rely on frontend timer)
                            if acc_res.get('success') and game.qayd_state.get('step') == 'RESULT':
                                _sherlock_log(f"  Auto-confirming verdict after 3s delay...")
                                sio.sleep(QAYD_RESULT_DELAY)  # Let frontend show the result (gevent-safe)
                                _sherlock_log(f"  Calling handle_qayd_confirm()...")
                                confirm_res = game.handle_qayd_confirm()
                                _sherlock_log(f"  Confirm result: {confirm_res}, phase={game.phase}")
                                
                                if confirm_res.get('success'):
                                    room_manager.save_game(game)
                                    broadcast_game_update(sio, game, room_id)
                                    
                                    if game.phase in ("FINISHED", "GAMEOVER"):
                                        sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                                        from server.socket_handler import auto_restart_round
                                        sio.start_background_task(auto_restart_round, game, room_id)
                        else:
                            _sherlock_log(f"  Follow-up was NOT QAYD_ACCUSATION, was: {follow_up}")
                        
                        return
                    else:
                        _sherlock_log(f"  Trigger FAILED: {res.get('error')}")
                
                elif action == 'QAYD_ACCUSATION':
                    logger.warning(f"[SHERLOCK] Bot {player.name} has accusation ready! Going atomic.")
                    accusation_data = decision.get('accusation', {})
                    res = game.handle_qayd_accusation(player.index, {
                        'crime_card': accusation_data.get('crime_card'),
                        'proof_card': accusation_data.get('proof_card'),
                        'violation_type': accusation_data.get('violation_type', 'REVOKE'),
                    })
                    
                    if res.get('success'):
                        logger.info(f"[SHERLOCK] Atomic accusation succeeded. Verdict: {game.qayd_state.get('verdict')}")
                        room_manager.save_game(game)
                        broadcast_game_update(sio, game, room_id)
                        
                        if game.phase in ("FINISHED", "GAMEOVER"):
                            sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                            from server.socket_handler import auto_restart_round
                            sio.start_background_task(auto_restart_round, game, room_id)
                        return
                    else:
                        logger.info(f"[SHERLOCK] Atomic accusation failed: {res.get('error')}")
        finally:
            game._sherlock_lock = False
    except Exception as e:
        import traceback
        _sherlock_log(f"EXCEPTION: {e}\n{traceback.format_exc()}")
        logger.error(f"Sherlock Watchdog Error: {e}")
        if hasattr(game, '_sherlock_lock'):
            game._sherlock_lock = False

def handle_sawa_responses(sio, game, room_id):
    """Trigger all bots to respond to a Sawa claim"""
    logger.info(f"Starting Sawa Responses for Room {room_id}")
    try:
        sio.sleep(SAWA_DELAY)
        
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
        
        # 1. Define next_idx early
        next_idx = game.current_turn
        
        # 2. Respect Qayd State (But allow REPORTER bot to continue investigation)
        qayd_state = game.qayd_state
        if qayd_state.get('active'):
            reporter_pos = qayd_state.get('reporter')
            # Use next_idx safely
            if 0 <= next_idx < len(game.players):
                current_player = game.players[next_idx]
            
                # Only the REPORTER can continue during Qayd
                is_reporter = (current_player.position == reporter_pos or 
                              str(next_idx) == str(reporter_pos) or
                              next_idx == reporter_pos)
            else:
                 is_reporter = False
            
            if not is_reporter:
                return  # Other bots wait
            
            # Reporter continues to investigation
            logger.info(f"[QAYD] Reporter bot {current_player.name} continuing investigation...")

        # next_idx is already defined now
        # if not game.players[next_idx].is_bot: ... checks below

        if not game.players[next_idx].is_bot:
            broadcast_game_update(sio, game, room_id)
            return

        # 2. Throttle Bot Loop (Prevent Freeze)
        sio.sleep(BOT_TURN_DELAY) 
        
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
             if res.get('success'):
                  broadcast_game_update(sio, game, room_id)
                  # Continue bot loop for accusation step
                  sio.start_background_task(bot_loop, sio, game, room_id, recursion_depth + 1)
                  return

        elif action == 'QAYD_ACCUSATION':
             print(f"[DEBUG] Bot sending QAYD_ACCUSATION: {decision.get('accusation')}")
             accusation_data = decision.get('accusation', {})
             
             res = game.handle_qayd_accusation(
                 current_idx,
                 {
                     'crime_card': accusation_data.get('crime_card'),
                     'proof_card': accusation_data.get('proof_card'),
                     'violation_type': accusation_data.get('violation_type', 'REVOKE'),
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
        
        if res and res.get('success'):
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
                 fallback_res = {'success': False, 'error': 'Unknown Phase'}
                 
                 if game.phase in ["BIDDING", "DOUBLING", "VARIANT_SELECTION"]:
                      # Fallback in auction is to PASS
                      fallback_res = game.handle_bid(current_idx, "PASS", None, reasoning="Fallback Pass")
                      
                 elif game.phase == "PLAYING":
                      # Fallback in playing is random card
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
        import traceback
        logger.error(f"Critical Bot Loop Error: {e}")
        logger.error(traceback.format_exc())
