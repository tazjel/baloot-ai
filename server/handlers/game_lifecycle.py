"""
Game lifecycle handlers: auto-restart, match snapshots, sawa timer, bot turn dispatch, bot dialogue.
"""
import time
import logging
import traceback

import server.bot_orchestrator as bot_orchestrator
from server.room_manager import room_manager
from ai_worker.personality import BALANCED, AGGRESSIVE, CONSERVATIVE
from ai_worker.dialogue_system import DialogueSystem
from ai_worker.memory_hall import memory_hall

logger = logging.getLogger(__name__)

dialogue_system = DialogueSystem()


def broadcast_game_update(sio, game, room_id):
    """Helper to emit validated game state with fallback"""
    from server.broadcast import broadcast_game_update as _broadcast
    _broadcast(sio, game, room_id)


def handle_bot_turn(sio, game, room_id):
    """Wrapper to trigger bot loop in background."""
    sio.start_background_task(bot_orchestrator.bot_loop, sio, game, room_id, 0)


def save_match_snapshot(game, room_id):
    """Helper to save match state to DB on round completion"""

    def debug_log(msg):
        try:
            with open("logs/archive_debug.txt", "a") as f:
                import datetime
                f.write(f"{datetime.datetime.now()} - {msg}\n")
        except OSError:
            pass

    try:
        debug_log(f"Attempting to save snapshot for room {room_id}")
        import json
        from server.common import db

        human = next((p for p in game.players if not p.is_bot), None)
        history_json = json.dumps(game.full_match_history, default=str)
        debug_log(f"History Length: {len(game.full_match_history)}")

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
        logger.exception(f"Snapshot Archive Failed: {e}")
        debug_log(f"EXCEPTION: {e}")
        debug_log(traceback.format_exc())


def _sawa_timer_task(sio, game, room_id, timer_seconds=3):
    """Background task: wait timer_seconds then auto-resolve pending Sawa."""
    try:
        sio.sleep(timer_seconds)

        # Check if Sawa is still pending (a human may have called SAWA_QAYD already)
        if not game.sawa_state.active or game.sawa_state.status != 'PENDING_TIMER':
            return  # Already resolved by human action

        result = game.handle_sawa_timeout()
        if result.get('success'):
            room_manager.save_game(game)
            broadcast_game_update(sio, game, room_id)

            if game.phase in ("FINISHED", "GAMEOVER"):
                sio.start_background_task(auto_restart_round, sio, game, room_id)
    except Exception as e:
        logger.error(f"Sawa timer task error: {e}")


def auto_restart_round(sio, game, room_id):
    """Wait then start next round if match is not over"""
    def _trace(msg):
        import datetime
        try:
            with open('logs/sherlock_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"{datetime.datetime.now().isoformat()} [AUTO_RESTART] {msg}\n")
        except OSError: pass
    
    try:
        # race condition guard
        if hasattr(game, 'is_restarting') and game.is_restarting:
            _trace(f"SKIPPED (is_restarting=True) for room {room_id}")
            logger.info(f"auto_restart_round: SKIPPED (is_restarting=True) for room {room_id}")
            return

        game.is_restarting = True
        _trace(f"ENTERED. Phase={game.phase}, room={room_id}")
        sio.sleep(0.5)  # Fast restart

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

        _trace(f"Phase check: {game.phase}")

        if game.phase == "FINISHED":
            _trace(f"FINISHED — calling save_to_archive + start_game")

            # Save Progress
            save_to_archive()

            if game.start_game():
                _trace(f"start_game() OK! New phase={game.phase}, emitting game_start")
                sio.emit('game_start', {'gameState': game.get_game_state()}, room=room_id)
                game.is_restarting = False  # Reset BEFORE bot loop
                _trace(f"Calling handle_bot_turn")
                handle_bot_turn(sio, game, room_id)
                return
            else:
                _trace(f"start_game() returned False!")
        elif game.phase == "GAMEOVER":
            logger.info(f"Match FINISHED for room {room_id} (152+ reached). Final score: US={game.match_scores['us']}, THEM={game.match_scores['them']}")

            # Save Final
            save_to_archive()

            # PERSIST LEGACY: Remember the match
            try:
                human = next((p for p in game.players if not p.is_bot), None)
                if human:
                    us_score = game.match_scores['us']
                    them_score = game.match_scores['them']

                    winner_team = 'us' if us_score >= 152 else 'them'
                    if human.index in [0, 2]:
                        player_won = (winner_team == 'us')
                    else:
                        player_won = (winner_team == 'them')

                    partner_idx = (human.index + 2) % 4
                    opp1_idx = (human.index + 1) % 4
                    opp2_idx = (human.index + 3) % 4

                    match_data = {
                        'winner': 'us' if player_won else 'them',
                        'my_partner': game.players[partner_idx].name,
                        'opponents': [game.players[opp1_idx].name, game.players[opp2_idx].name],
                        'score_us': us_score if human.index in [0, 2] else them_score,
                        'score_them': them_score if human.index in [0, 2] else us_score
                    }

                    memory_hall.remember_match(human.id, human.name, match_data)
            except Exception as mem_err:
                logger.error(f"Failed to save memory: {mem_err}")
        else:
            logger.warning(f"auto_restart_round: Unexpected phase '{game.phase}' for room {room_id}")

    except Exception as e:
        logger.error(f"Error in auto_restart_round: {e}")
    finally:
        # ALWAYS clear the flag to prevent permanent freeze
        if game:
            game.is_restarting = False


def handle_bot_speak(sio, game, room_id, player, action, result):
    """Generate and emit bot dialogue"""
    try:
        personality = BALANCED
        if "khalid" in player.avatar:
            personality = AGGRESSIVE
        elif "abu_fahad" in player.avatar:
            personality = CONSERVATIVE
        elif "saad" in player.avatar:
            personality = BALANCED

        context = f"Did action: {action}."
        if action == 'AKKA':
            context += " I declared Akka (Highest Non-Trump). I command this suit!"

        if game.last_trick and action == 'PLAY':
            winner = game.last_trick.get('winner') if isinstance(game.last_trick, dict) else getattr(game.last_trick, 'winner', None)
            if winner == player.position:
                context += " I won this trick."

        if game.phase == "BIDDING":
            bid_type = game.bid.get('type') if isinstance(game.bid, dict) else getattr(game.bid, 'type', 'None')
            context += f" Current Bid: {bid_type or 'None'}."

        human = next((p for p in game.players if not p.is_bot), None)
        rivalry_summary = {}
        if human:
            rivalry_summary = memory_hall.get_rivalry_summary(human.id)

        text = dialogue_system.generate_reaction(player.name, personality, context, game_state=None, rivalry_summary=rivalry_summary)

        if text:
            sio.emit('bot_speak', {
                'playerIndex': player.index,
                'text': text,
                'emotion': 'neutral'
            }, room=room_id)

    except Exception as e:
        logger.error(f"Error in handle_bot_speak: {e}")
