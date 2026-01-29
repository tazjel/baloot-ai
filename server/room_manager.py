from server.game_logic import Game
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
        pid = os.getpid()
        if not room_id: return None
        
        # 1. Try Redis First
        try:
            if redis_store:
                data = redis_store.get(f"game:{room_id}")
                if data:
                    g = pickle.loads(data)
                    logger.info(f"[PID:{pid}] Redis GET {room_id} -> Found")
                    return g
                else:
                    logger.info(f"[PID:{pid}] Redis GET {room_id} -> MISS")
            else:
                 logger.info(f"[PID:{pid}] Redis GET {room_id} -> RedisStore is NONE")
        except Exception as e:
            logger.error(f"[PID:{pid}] Error fetching game {room_id} from Redis: {e}")
        
        # 2. Fallback to Local Memory (Vital for transient or failed-save scenarios)
        local = self._local_cache.get(room_id)
        if local:
             logger.info(f"[PID:{pid}] Local GET {room_id} -> Found")
        else:
             logger.info(f"[PID:{pid}] Local GET {room_id} -> MISS")
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
