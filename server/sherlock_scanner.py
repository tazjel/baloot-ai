"""
server/sherlock_scanner.py — Forensic Watchdog for Bot-Detected Illegal Moves.

Extracted from bot_orchestrator.py for separation of concerns.
Runs independently to detect illegal card plays and trigger Qayd via QaydEngine.
"""
import logging
import datetime
import traceback

from ai_worker.agent import bot_agent
from server.broadcast import broadcast_game_update
from server.room_manager import room_manager
import server.settings as settings

logger = logging.getLogger(__name__)

# Timing config (from centralized settings)
QAYD_RESULT_DELAY = settings.QAYD_RESULT_DELAY


def _sherlock_log(msg):
    """Write debug line to sherlock_debug.log"""
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
                                        _sherlock_log(f"  Phase is {game.phase}, calling auto_restart_round. is_restarting={getattr(game, 'is_restarting', 'N/A')}")
                                        sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                                        from server.handlers.game_lifecycle import auto_restart_round
                                        sio.start_background_task(auto_restart_round, sio, game, room_id)
                                        _sherlock_log(f"  auto_restart_round bg task launched")
                                    else:
                                        _sherlock_log(f"  Phase is {game.phase}, NOT calling auto_restart")
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
                            from server.handlers.game_lifecycle import auto_restart_round
                            sio.start_background_task(auto_restart_round, sio, game, room_id)
                        return
                    else:
                        logger.info(f"[SHERLOCK] Atomic accusation failed: {res.get('error')}")
        finally:
            game._sherlock_lock = False
    except Exception as e:
        _sherlock_log(f"EXCEPTION: {e}\n{traceback.format_exc()}")
        logger.error(f"Sherlock Watchdog Error: {e}")
        if hasattr(game, '_sherlock_lock'):
            game._sherlock_lock = False
