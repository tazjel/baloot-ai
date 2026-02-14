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

MAX_ROOMS = 500  # Maximum concurrent rooms to prevent memory exhaustion


class RoomManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RoomManager, cls).__new__(cls)
            cls._instance._local_cache = {}
            cls._instance._sid_to_room: dict[str, str] = {}  # SID → room_id
        return cls._instance

    def create_room(self):
        # Enforce max rooms limit
        active_count = len(self._local_cache)
        if active_count >= MAX_ROOMS:
            logger.warning(f"Max rooms limit reached ({MAX_ROOMS}). Denying create_room.")
            return None

        room_id = str(uuid.uuid4())[:8]
        game = Game(room_id)
        self.save_game(game)
        rlog = GameLoggerAdapter(logger, room_id=room_id)
        rlog.info("Created room (Persisted to Redis)")
        return room_id

    def track_player(self, sid: str, room_id: str):
        """Track which room a player (SID) belongs to for disconnect cleanup."""
        self._sid_to_room[sid] = room_id

    def untrack_player(self, sid: str):
        """Remove player tracking on disconnect."""
        self._sid_to_room.pop(sid, None)

    def get_room_for_sid(self, sid: str):
        """Return the room_id a given SID is in, or None."""
        return self._sid_to_room.get(sid)

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
                # Update local cache ONLY after Redis write succeeds
                self._local_cache[game.room_id] = game
            else:
                # No Redis — local cache is the only storage
                self._local_cache[game.room_id] = game
                rlog.info("Redis SAVE -> SKIPPED (No RedisStore)")
        except (TypeError, ValueError) as e:
            rlog.error(f"Serialization Error: {e}")
        except ConnectionError as e:
            rlog.error(f"Redis Connection Error saving: {e}")
            # Still update local cache as fallback when Redis is down
            self._local_cache[game.room_id] = game
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
            # Use SCAN instead of KEYS to avoid blocking Redis on large datasets
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = redis_store.scan(cursor=cursor, match="game:*", count=100)
                if keys:
                    redis_store.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            if deleted:
                logger.warning(f"CLEARED {deleted} Zombie Games from Redis.")
        except ConnectionError as e:
            logger.error(f"Failed to clear Redis games (connection): {e}")
        except Exception as e:
            logger.exception(f"Failed to clear Redis games: {e}")
        
    @property
    def games(self):
        all_games = {}
        if not redis_store: return self._local_cache

        try:
            # Use SCAN instead of KEYS to avoid blocking Redis
            cursor = 0
            while True:
                cursor, keys = redis_store.scan(cursor=cursor, match="game:*", count=100)
                for k in keys:
                    rid = k.decode('utf-8').split(":")[-1] if isinstance(k, bytes) else k.split(":")[-1]
                    game = self.get_game(rid)
                    if game: all_games[rid] = game
                if cursor == 0:
                    break
            return all_games
        except ConnectionError as e:
             logger.error(f"Error listing Redis games (connection): {e}")
             return self._local_cache
        except Exception as e:
             logger.exception(f"Error listing Redis games: {e}")
             return self._local_cache

# Global instance
room_manager = RoomManager()
