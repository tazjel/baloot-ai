"""
server/broadcast.py — Canonical broadcast module.

Single source of truth for emitting validated game state to clients.
All modules should import broadcast_game_update from here.
"""
import json
import logging

logger = logging.getLogger(__name__)


def broadcast_game_update(sio, game, room_id):
    """Emit validated game state with schema check and fallback."""
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
