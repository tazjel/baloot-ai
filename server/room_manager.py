"""
server/room_manager.py — Game persistence via Redis using JSON serialization.

Single source of truth for game state storage. Uses Game.to_json() / Game.from_json()
instead of pickle for security and compatibility.
"""
from game_engine.logic.game import Game
import json
import uuid
import logging
import os
from server.common import redis_client, redis_store
from server.exceptions import RedisPersistenceError, SerializationError
from server.logging_utils import GameLoggerAdapter

logger = logging.getLogger(__name__)

class RoomManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RoomManager, cls).__new__(cls)
            cls._instance._local_cache = {} 
        return cls._instance

    def create_room(self):
        room_id = str(uuid.uuid4())[:8]
        game = Game(room_id)
        self.save_game(game)
        rlog = GameLoggerAdapter(logger, room_id=room_id)
        rlog.info("Created room (Persisted to Redis)")
        return room_id

    def get_game(self, room_id):
        if not room_id: return None
        rlog = GameLoggerAdapter(logger, room_id=room_id)
        
        # 1. Try Redis (Primary Truth)
        try:
            if redis_store:
                data = redis_store.get(f"game:{room_id}")
                if data:
                    game_dict = json.loads(data)
                    g = Game.from_json(game_dict)
                    if self._instance: 
                        self._instance._local_cache[room_id] = g
                    return g
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            rlog.error(f"Deserialization Error: {e}")
        except ConnectionError as e:
            rlog.error(f"Redis Connection Error: {e}")
        except Exception as e:
            rlog.exception(f"Unexpected Redis GET Error: {e}")
        
        # 2. Fallback to Local Memory
        local = self._local_cache.get(room_id)
        if local:
             rlog.warning("Serving Local Stale Game (Redis Miss)")
        return local

    def save_game(self, game):
        if not game: return
        rlog = GameLoggerAdapter(logger, room_id=game.room_id)
        try:
            self._local_cache[game.room_id] = game
            
            if redis_store:
                def _json_fallback(obj):
                    """Safety net for objects that slip through to_json()."""
                    if hasattr(obj, 'to_dict'):
                        return obj.to_dict()
                    if hasattr(obj, 'value'):  # Enum
                        return obj.value
                    raise TypeError(f"Unable to serialize: {type(obj)}")
                game_json = json.dumps(game.to_json(), default=_json_fallback)
                redis_store.setex(f"game:{game.room_id}", 3600, game_json)
            else:
                rlog.info("Redis SAVE -> SKIPPED (No RedisStore)")
        except (TypeError, ValueError) as e:
            rlog.error(f"Serialization Error: {e}")
        except ConnectionError as e:
            rlog.error(f"Redis Connection Error saving: {e}")
        except Exception as e:
            rlog.exception(f"Unexpected error saving game: {e}")

    def remove_room(self, room_id):
        if room_id in self._local_cache:
            del self._local_cache[room_id]
            
        if redis_store:
            redis_store.delete(f"game:{room_id}")
            return True
        return False

    def clear_all_games(self):
        """Dev utility to clear all persisted games from Redis on startup."""
        if not redis_store: return
        try:
            keys = redis_store.keys("game:*")
            if keys:
                redis_store.delete(*keys)
                logger.warning(f"CLEARED {len(keys)} Zombie Games from Redis.")
        except ConnectionError as e:
            logger.error(f"Failed to clear Redis games (connection): {e}")
        except Exception as e:
            logger.exception(f"Failed to clear Redis games: {e}")
        
    @property
    def games(self):
        all_games = {}
        if not redis_store: return self._local_cache
        
        try:
            keys = redis_store.keys("game:*")
            for k in keys:
                rid = k.decode('utf-8').split(":")[-1]
                game = self.get_game(rid)
                if game: all_games[rid] = game
            return all_games
        except ConnectionError as e:
             logger.error(f"Error listing Redis games (connection): {e}")
             return self._local_cache
        except Exception as e:
             logger.exception(f"Error listing Redis games: {e}")
             return self._local_cache

# Global instance
room_manager = RoomManager()
