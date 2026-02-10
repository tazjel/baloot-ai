"""
server/bot_orchestrator.py — Bot turn orchestration.

Manages bot decision-making and action execution using a strategy pattern.
Each game phase (AKKA, SAWA, QAYD, BIDDING, PLAYING) is handled by a
dedicated function rather than a monolithic if-elif chain.
"""
import time
import logging
from ai_worker.agent import bot_agent
from server.broadcast import broadcast_game_update
from server.room_manager import room_manager
import server.settings as settings
from server.logging_utils import GameLoggerAdapter

logger = logging.getLogger(__name__)

def _room_logger(room_id: str) -> GameLoggerAdapter:
    """Create a logger adapter with room_id context for structured logging."""
    return GameLoggerAdapter(logger, room_id=room_id)


# ── Bot Speed Configuration (from centralized settings) ──────────
BOT_TURN_DELAY    = settings.BOT_TURN_DELAY
QAYD_RESULT_DELAY = settings.QAYD_RESULT_DELAY
SAWA_DELAY        = settings.SAWA_DELAY

from server.sherlock_scanner import run_sherlock_scan, _sherlock_log


# ── Strategy Handlers ─────────────────────────────────────────────

def _handle_akka(game, current_idx, decision):
    """Handle bot Akka declaration."""
    return game.handle_akka(current_idx)


def _handle_sawa(sio, game, room_id, current_idx, decision):
    """Handle bot Sawa claim. Returns True if round ended (caller should exit)."""
    res = game.handle_sawa(current_idx)
    if res.get('success'):
        broadcast_game_update(sio, game, room_id)
        room_manager.save_game(game)
        if game.phase in ("FINISHED", "GAMEOVER"):
            from server.handlers.game_lifecycle import auto_restart_round
            sio.start_background_task(auto_restart_round, sio, game, room_id)
        return res, True  # Signal: exit bot loop
    return res, False


def _handle_qayd_trigger(sio, game, room_id, current_idx, decision, recursion_depth):
    """Handle bot triggering Qayd investigation."""
    res = game.handle_qayd_trigger(current_idx)
    if res.get('success'):
        broadcast_game_update(sio, game, room_id)
        sio.start_background_task(bot_loop, sio, game, room_id, recursion_depth + 1)
        return res, True  # Signal: exit bot loop
    return res, False


def _handle_qayd_accusation(game, current_idx, decision):
    """Handle bot submitting Qayd accusation."""
    logger.debug(f"Bot sending QAYD_ACCUSATION: {decision.get('accusation')}")
    accusation_data = decision.get('accusation', {})
    return game.handle_qayd_accusation(
        current_idx,
        {
            'crime_card': accusation_data.get('crime_card'),
            'proof_card': accusation_data.get('proof_card'),
            'violation_type': accusation_data.get('violation_type', 'REVOKE'),
        }
    )


def _handle_qayd_cancel(game):
    """Handle bot cancelling Qayd."""
    return game.handle_qayd_cancel()


def _handle_bidding(game, current_idx, decision):
    """Handle bot bidding action."""
    action = (decision.get('action') or 'PASS').upper()
    suit = decision.get('suit')
    reasoning = decision.get('reasoning')
    return game.handle_bid(current_idx, action, suit, reasoning=reasoning)


def _handle_playing(game, current_idx, decision):
    """Handle bot playing a card."""
    card_idx = decision.get('cardIndex', 0)
    reasoning = decision.get('reasoning')
    metadata = {}
    if reasoning:
        metadata['reasoning'] = reasoning
    if decision.get('declarations'):
        metadata['declarations'] = decision['declarations']
    return game.play_card(current_idx, card_idx, metadata=metadata)


def _execute_fallback(sio, game, room_id, current_idx, recursion_depth):
    """Fallback when primary action fails: PASS for bidding, card[0] for playing."""
    if game.is_locked:
        logger.info(f"[{room_id}] Bot action failed due to Game Lock (Qayd). Skipping fallback.")
        return

    current_phase = game.phase
    fallback_res = {'success': False, 'error': 'Unknown Phase'}

    if current_phase in ["BIDDING", "DOUBLING", "VARIANT_SELECTION"]:
        fallback_res = game.handle_bid(current_idx, "PASS", None, reasoning="Fallback Pass")
    elif current_phase == "PLAYING":
        fallback_res = game.play_card(current_idx, 0, metadata={'reasoning': 'Fallback Random'})
    else:
        logger.info(f"[{room_id}] Bot fallback: phase is now '{current_phase}', re-entering bot loop.")
        sio.start_background_task(bot_loop, sio, game, room_id, recursion_depth + 1)
        return

    if fallback_res.get('success'):
        broadcast_game_update(sio, game, room_id)
        room_manager.save_game(game)
        sio.start_background_task(bot_loop, sio, game, room_id, recursion_depth + 1)
    else:
        logger.critical(f"[{room_id}] Bot Fallback Failed too: {fallback_res}. Game might be stuck.")


# ── Action Dispatch Table ─────────────────────────────────────────

# Maps action names to their handler functions.
# Handlers that need sio/room_id receive them via bot_loop.
ACTION_HANDLERS = {
    'AKKA':             lambda **kw: (_handle_akka(kw['game'], kw['current_idx'], kw['decision']), False),
    'QAYD_CANCEL':      lambda **kw: (_handle_qayd_cancel(kw['game']), False),
}


# ── Main Bot Loop ─────────────────────────────────────────────────

def bot_loop(sio, game, room_id, recursion_depth=0):
    """Background task to handle consecutive bot turns."""
    rlog = _room_logger(room_id)
    try:
        # Safety: prevent infinite recursion
        if recursion_depth > 500:
            rlog.warning(f"Bot Loop Safety Break (Depth {recursion_depth})")
            return

        if not game or not game.players:
            return

        if game.phase not in ["BIDDING", "PLAYING", "DOUBLING", "VARIANT_SELECTION"]:
            _sherlock_log(f"[BOT_LOOP] EXIT: phase={game.phase} not in allowed phases. depth={recursion_depth}")
            return

        if game.current_turn < 0 or game.current_turn >= len(game.players):
            return

        next_idx = game.current_turn

        # ── Qayd Gate: only reporter bot may act during active Qayd ──
        qayd_state = game.qayd_state
        if qayd_state.get('active'):
            reporter_pos = qayd_state.get('reporter')
            if 0 <= next_idx < len(game.players):
                current_player = game.players[next_idx]
                is_reporter = (current_player.position == reporter_pos or
                               str(next_idx) == str(reporter_pos) or
                               next_idx == reporter_pos)
            else:
                is_reporter = False

            if not is_reporter:
                _sherlock_log(f"[BOT_LOOP] EXIT: qayd active, bot {next_idx} is not reporter ({reporter_pos}). depth={recursion_depth}")
                return

            rlog.info(f"[QAYD] Reporter bot {current_player.name} continuing investigation...")

        # ── Human check ──
        if not game.players[next_idx].is_bot:
            _sherlock_log(f"[BOT_LOOP] EXIT: player {next_idx} ({game.players[next_idx].name}) is human. phase={game.phase}. depth={recursion_depth}.")
            broadcast_game_update(sio, game, room_id)
            return

        # ── Throttle ──
        sio.sleep(BOT_TURN_DELAY)

        if game.phase == "FINISHED":
            return

        current_idx = game.current_turn
        current_player = game.players[current_idx]

        if not current_player.is_bot:
            return

        # ── Get AI Decision ──
        decision = bot_agent.get_decision(game.get_game_state(), current_idx)
        action = decision.get('action')
        res = {'success': False}

        # ── Dispatch to strategy handler ──
        should_exit = False

        if action == 'AKKA':
            res = _handle_akka(game, current_idx, decision)
        elif action == 'SAWA':
            res, should_exit = _handle_sawa(sio, game, room_id, current_idx, decision)
        elif action == 'QAYD_TRIGGER':
            res, should_exit = _handle_qayd_trigger(sio, game, room_id, current_idx, decision, recursion_depth)
        elif action == 'QAYD_ACCUSATION':
            res = _handle_qayd_accusation(game, current_idx, decision)
        elif action == 'QAYD_CANCEL':
            res = _handle_qayd_cancel(game)
        elif game.phase in ["BIDDING", "DOUBLING", "VARIANT_SELECTION"]:
            res = _handle_bidding(game, current_idx, decision)
        elif game.phase == "PLAYING":
            res = _handle_playing(game, current_idx, decision)

        if should_exit:
            return

        # ── Post-action processing ──
        if res and res.get('success'):
            broadcast_game_update(sio, game, room_id)
            sio.start_background_task(run_sherlock_scan, sio, game, room_id)

            if game.phase == "FINISHED":
                room_manager.save_game(game)
                return

            room_manager.save_game(game)
            sio.start_background_task(bot_loop, sio, game, room_id, recursion_depth + 1)
        else:
            rlog.error(f"Bot Action Failed: {res}. Attempting Fallback.")
            try:
                _execute_fallback(sio, game, room_id, current_idx, recursion_depth)
            except Exception as fe:
                rlog.exception(f"Fallback Exception: {fe}")

    except Exception as e:
        rlog.exception(f"Critical Bot Loop Error: {e}")
