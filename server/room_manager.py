from game_engine.logic.game import Game
import uuid
import pickle
import logging
import os
from server.common import redis_client, redis_store

logger = logging.getLogger(__name__)

class RoomManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RoomManager, cls).__new__(cls)
            # Memory cache for very hot access (optional, but good for performance)
            # key: room_id, value: { 'game': Game, 'timestamp': time }
            cls._instance._local_cache = {} 
        return cls._instance

    def create_room(self):
        room_id = str(uuid.uuid4())[:8]
        game = Game(room_id)
        self.save_game(game)
        logger.info(f"Created room {room_id} (Persisted to Redis)")
        return room_id

    def get_game(self, room_id):
        # PID used for process isolation tracking
        pid = os.getpid()
        if not room_id: return None
        
        # 1. Try Redis (Primary Truth)
        try:
            if redis_store:
                data = redis_store.get(f"game:{room_id}")
                if data:
                    g = pickle.loads(data)
                    # Sync local cache just in case, but Redis is truth
                    if self._instance: 
                        self._instance._local_cache[room_id] = g
                    return g
        except Exception as e:
            logger.error(f"[PID:{pid}] Redis GET Error {room_id}: {e}")
        
        # 2. Fallback to Local Memory (Only if Redis fails or is missing)
        # In a generic/stateless fleet, this will likely be a MISS, which is correct.
        local = self._local_cache.get(room_id)
        if local:
             logger.warning(f"[PID:{pid}] Serving Local Stale Game {room_id} (Redis Miss)")
        return local

    def save_game(self, game):
        pid = os.getpid()
        if not game: return
        try:
            # Update Local Cache (ALWAYS)
            self._local_cache[game.room_id] = game
            logger.info(f"[PID:{pid}] Local SAVE {game.room_id}")
            
            if redis_store:
                # 1 Hour Expiry for active games
                redis_store.setex(f"game:{game.room_id}", 3600, pickle.dumps(game))
                logger.info(f"[PID:{pid}] Redis SAVE {game.room_id} -> OK")
            else:
                logger.info(f"[PID:{pid}] Redis SAVE {game.room_id} -> SKIPPED (No RedisStore)")
        except Exception as e:
            logger.error(f"[PID:{pid}] Error saving game {game.room_id} to Redis: {e}")
            pass

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
                logger.warning(f"🧹 CLEARED {len(keys)} Zombie Games from Redis.")
        except Exception as e:
            logger.error(f"Failed to clear Redis games: {e}")
        
    @property
    def games(self):
        # Compatibility property for code iterating directly over .games
        # Warning: This iterates ALL keys in Redis, which is slow.
        # Should be avoided in high-performance paths.
        all_games = {}
        if not redis_store: return self._local_cache
        
        try:
            keys = redis_store.keys("game:*")
            for k in keys:
                rid = k.decode('utf-8').split(":")[-1] # Decode key manually since client is binary
                game = self.get_game(rid)
                if game: all_games[rid] = game
            return all_games
        except:
             return self._local_cache

# Global instance
room_manager = RoomManager()
