"""
Core game_action event handler — dispatches BID, PLAY, QAYD, SAWA, AKKA, etc.
"""
import logging

import server.bot_orchestrator as bot_orchestrator
from server.room_manager import room_manager
from server.rate_limiter import limiter
from server.handlers.game_lifecycle import (
    broadcast_game_update, handle_bot_turn,
    save_match_snapshot, auto_restart_round,
    _sawa_timer_task,
)

logger = logging.getLogger(__name__)

VALID_ACTIONS = {
    'BID', 'PLAY', 'DECLARE_PROJECT', 'DOUBLE',
    'SAWA', 'SAWA_CLAIM', 'SAWA_QAYD', 'QAYD',
    'QAYD_TRIGGER', 'QAYD_MENU_SELECT', 'QAYD_VIOLATION_SELECT',
    'QAYD_SELECT_CRIME', 'QAYD_SELECT_PROOF', 'QAYD_ACCUSATION',
    'QAYD_CONFIRM', 'QAYD_CANCEL', 'AKKA',
    'UPDATE_SETTINGS', 'NEXT_ROUND',
}


def register(sio):
    """Register the game_action event handler on the given sio instance."""

    @sio.event
    def game_action(sid, data):
        if not isinstance(data, dict):
            return {'success': False, 'error': 'Invalid request format'}

        room_id = data.get('roomId')
        action = data.get('action')
        payload = data.get('payload', {})

        # Validate input types
        if not isinstance(room_id, str) or not room_id or len(room_id) > 64:
            return {'success': False, 'error': 'Invalid roomId'}
        if not isinstance(action, str) or action not in VALID_ACTIONS:
            return {'success': False, 'error': f'Unknown action: {action}'}
        if not isinstance(payload, dict):
            payload = {}

        game = room_manager.get_game(room_id)
        if not game:
            return {'success': False, 'error': 'Game not found'}

        # Rate Limit: 20 per second per SID
        if not limiter.check_limit(f"game_action:{sid}", 20, 1):
            return {'success': False, 'error': 'Too many actions'}

        # Find player
        player = next((p for p in game.players if p.id == sid), None)
        if not player:
            return {'success': False, 'error': 'Player not in this game'}

        result = _dispatch_action(sio, game, player, action, payload, room_id)

        if result.get('success'):
            _handle_success(sio, game, player, action, result, room_id)
        else:
            if 'error' in result:
                logger.warning(f"Action '{action}' failed for {player.position}: {result['error']}")

        return result


def _dispatch_action(sio, game, player, action, payload, room_id):
    """Route the action to the appropriate game method."""
    result = {'success': False}

    if action == 'BID':
        bid_action = payload.get('action')
        bid_suit = payload.get('suit')
        if bid_action is not None and not isinstance(bid_action, str):
            return {'success': False, 'error': 'Invalid bid action type'}
        if bid_suit is not None and (not isinstance(bid_suit, str) or bid_suit not in ('♠', '♥', '♦', '♣')):
            return {'success': False, 'error': f'Invalid bid suit: {bid_suit}'}
        result = game.handle_bid(player.index, bid_action, bid_suit)

    elif action == 'PLAY':
        result = _handle_play(game, player, payload)

    elif action == 'DECLARE_PROJECT':
        result = game.handle_declare_project(player.index, payload.get('type'))

    elif action == 'DOUBLE':
        result = game.handle_double(player.index)

    elif action in ('SAWA', 'SAWA_CLAIM'):
        if hasattr(game, 'handle_sawa'):
            result = game.handle_sawa(player.index)
        else:
            result = {'success': False, 'error': 'Sawa not implemented backend'}

    elif action == 'SAWA_QAYD':
        if hasattr(game, 'handle_sawa_qayd'):
            result = game.handle_sawa_qayd(player.index)
        else:
            result = {'success': False, 'error': 'Sawa Qayd not implemented'}

    elif action == 'QAYD':
        result = game.handle_qayd(player.index, payload.get('reason'))

    # --- FORENSIC (VAR) ACTIONS ---
    elif action == 'QAYD_TRIGGER':
        logger.info(f"[SOCKET] QAYD_TRIGGER from player {player.index}")
        result = game.handle_qayd_trigger(player.index)

    elif action == 'QAYD_MENU_SELECT':
        result = game.handle_qayd_menu_select(player.index, payload.get('option'))

    elif action == 'QAYD_VIOLATION_SELECT':
        result = game.handle_qayd_violation_select(player.index, payload.get('violation_type'))

    elif action == 'QAYD_SELECT_CRIME':
        result = game.handle_qayd_select_crime(player.index, payload)

    elif action == 'QAYD_SELECT_PROOF':
        result = game.handle_qayd_select_proof(player.index, payload)

    elif action == 'QAYD_ACCUSATION':
        logger.debug(f"QAYD_ACCUSATION received: {payload.get('accusation')}")
        result = game.handle_qayd_accusation(player.index, payload.get('accusation'))
        logger.debug(f"QAYD_ACCUSATION result: {result}")

    elif action == 'QAYD_CONFIRM':
        logger.info(f"[SOCKET] QAYD_CONFIRM received")
        bot_orchestrator._sherlock_log(f"QAYD_CONFIRM from {player.position}. qayd_state={game.qayd_state}")
        result = game.handle_qayd_confirm()
        bot_orchestrator._sherlock_log(f"QAYD_CONFIRM result={result}, phase={game.phase}")

        # Trigger auto-restart if game finished (Qayd Penalty applied)
        if result.get('success') and game.phase in ["FINISHED", "GAMEOVER"]:
            room_manager.save_game(game)
            broadcast_game_update(sio, game, room_id)
            sio.start_background_task(auto_restart_round, sio, game, room_id)
            return result  # Skip normal broadcast below

    elif action == 'QAYD_CANCEL':
        result = game.handle_qayd_cancel()
        if result.get('trigger_next_round'):
            sio.start_background_task(auto_restart_round, sio, game, room_id)

    elif action == 'AKKA':
        result = game.handle_akka(player.index)

    elif action == 'UPDATE_SETTINGS':
        if 'turnDuration' in payload:
            try:
                td = float(payload['turnDuration'])
                if not (1.0 <= td <= 120.0):
                    return {'success': False, 'error': 'turnDuration must be between 1 and 120 seconds'}
                game.turn_duration = td
                logger.info(f"Updated Turn Duration to {game.turn_duration}s for room {room_id}")
            except (TypeError, ValueError):
                return {'success': False, 'error': 'Invalid turnDuration value'}
        if 'strictMode' in payload:
            game.strictMode = bool(payload['strictMode'])
            logger.info(f"Updated strictMode to {game.strictMode} for room {room_id}")
        result = {'success': True}

    elif action == 'NEXT_ROUND':
        result = _handle_next_round(sio, game, room_id)

    # Log QAYD actions for debug
    if action.startswith('QAYD'):
        logger.debug(f"QAYD ACTION RECEIVED: {action} from {player.name} ({player.index})")
        logger.info(f"[SOCKET] QAYD ACTION RECEIVED: {action}")

    return result


def _handle_play(game, player, payload):
    """Handle PLAY action with validated cardIndex."""
    card_index = payload.get('cardIndex')
    if not isinstance(card_index, int) or card_index < 0 or card_index > 7:
        return {'success': False, 'error': f'Invalid cardIndex: {card_index}'}

    metadata = payload.get('metadata', {})
    if not isinstance(metadata, dict):
        metadata = {}
    if 'cardId' in payload:
        metadata['cardId'] = payload['cardId']

    return game.play_card(player.index, card_index, metadata=metadata)


def _handle_next_round(sio, game, room_id):
    """Handle NEXT_ROUND action."""
    if game.phase == "FINISHED":
        logger.info(f"Starting Next Round for room {room_id} by request.")
        if game.start_game():
            sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
            handle_bot_turn(sio, game, room_id)
        return {'success': True}

    elif game.phase == "GAMEOVER":
        logger.info(f"Starting New Match (Rematch) for room {room_id} by request.")
        game.match_scores = {'us': 0, 'them': 0}
        game.past_round_results = []
        game.full_match_history = []

        if game.start_game():
            sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
            handle_bot_turn(sio, game, room_id)
        room_manager.save_game(game)
        return {'success': True}

    return {'success': False, 'error': 'Cannot start round, phase is ' + game.phase}


def _handle_success(sio, game, player, action, result, room_id):
    """Post-success: persist, broadcast, trigger bots."""
    # PERSIST STATE TO REDIS
    room_manager.save_game(game)

    # Broadcast Update to all clients
    broadcast_game_update(sio, game, room_id)

    # --- SAWA: Handle instant resolution or timer ---
    if action in ('SAWA', 'SAWA_CLAIM'):
        if result.get('sawa_resolved') or result.get('sawa_penalty'):
            if game.phase in ("FINISHED", "GAMEOVER"):
                sio.start_background_task(auto_restart_round, sio, game, room_id)
                return
        elif result.get('sawa_pending_timer'):
            timer_seconds = result.get('timer_seconds', 3)
            sio.start_background_task(_sawa_timer_task, sio, game, room_id, timer_seconds)
            return  # Don't trigger bot loop while timer is active

    if action == 'SAWA_QAYD':
        if game.phase in ("FINISHED", "GAMEOVER"):
            sio.start_background_task(auto_restart_round, sio, game, room_id)
            return

    # --- SHERLOCK WATCHDOG ---
    bot_orchestrator._sherlock_log(f"SOCKET: Launching Sherlock scan after action '{action}' by {player.position}")
    sio.start_background_task(bot_orchestrator.run_sherlock_scan, sio, game, room_id)

    # Trigger Bot Loop (Background)
    try:
        sio.start_background_task(bot_orchestrator.bot_loop, sio, game, room_id)
    except Exception as e:
        logger.error(f"Failed to start bot task: {e}")

    # Check if game finished to trigger auto-restart
    if game.phase == "FINISHED":
        save_match_snapshot(game, room_id)
