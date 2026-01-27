import logging
import json
import time

# Settings
try:
    from server.settings import REDIS_URL, OFFLINE_MODE
except ImportError:
    REDIS_URL = "redis://localhost:6379/0"
    OFFLINE_MODE = False

# Redis
try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

class MemoryHall:
    """
    The 'Memory Hall' stores long-term narrative data about players.
    - Rivalries (Wins/Losses vs specific Bots)
    - Play Styles
    - Past Glories/Shames
    """
    def __init__(self):
        self.redis_client = None
        self._connect()

    def _connect(self):
        if OFFLINE_MODE:
             return

        if redis:
            try:
                self.redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1.0)
                logger.info("[MEMORY_HALL] Connected to Redis.")
            except Exception as e:
                logger.error(f"[MEMORY_HALL] Redis connection failed: {e}")

    def remember_match(self, user_id: str, player_name: str, match_data: dict):
        """
        Updates the rivalry stats for a user after a match.
        match_data: {
          'winner': 'us' | 'them',
          'my_partner': 'Khalid',
          'opponents': ['Saad', 'Fahad'],
          'score_us': 152,
          'score_them': 100
        }
        """
        if not self.redis_client or not user_id:
            return

        try:
            key = f"rivalry:{user_id}"
            
            # 1. Update Basic Stats
            self.redis_client.hincrby(key, "games_played", 1)
            
            if match_data['winner'] == 'us':
                self.redis_client.hincrby(key, "wins_vs_ai", 1)
            else:
                self.redis_client.hincrby(key, "losses_vs_ai", 1)
                
            # 2. Update Specific Bot Relationships
            rel_key = f"rivalry:{user_id}:relationships"
            
            # Partner
            partner = match_data.get('my_partner')
            if partner:
                res = "won_with" if match_data['winner'] == 'us' else "lost_with"
                self.redis_client.hincrby(rel_key, f"{partner}:{res}", 1)
                
            # Opponents
            for opp in match_data.get('opponents', []):
                res = "won_against" if match_data['winner'] == 'us' else "lost_to"
                self.redis_client.hincrby(rel_key, f"{opp}:{res}", 1)

            logger.info(f"[MEMORY_HALL] Remembered match for {player_name} ({user_id})")

        except Exception as e:
            logger.error(f"[MEMORY_HALL] Failed to remember match: {e}")

    def get_rivalry_summary(self, user_id: str) -> dict:
        """
        Returns a summary of the user's history for dialogue injection.
        """
        if not self.redis_client or not user_id:
            return {}

        try:
            key = f"rivalry:{user_id}"
            stats = self.redis_client.hgetall(key)
            
            if not stats: 
                return {"status": "stranger"}
            
            games = int(stats.get('games_played', 0))
            wins = int(stats.get('wins_vs_ai', 0))
            losses = int(stats.get('losses_vs_ai', 0))
            
            win_rate = 0
            if games > 0:
                win_rate = (wins / games) * 100
                
            # Calculate Nemesis (Most 'lost_to')
            rel_key = f"rivalry:{user_id}:relationships"
            rels = self.redis_client.hgetall(rel_key)
            
            nemesis = None
            max_losses = 0
            
            for k, v in rels.items():
                if k.endswith(":lost_to"):
                    bot_name = k.split(":")[0]
                    count = int(v)
                    if count > max_losses:
                        max_losses = count
                        nemesis = bot_name
                        
            return {
                "status": "regular" if games > 5 else "novice",
                "games_played": games,
                "win_rate": round(win_rate, 1),
                "nemesis": nemesis,
                "total_wins": wins,
                "total_losses": losses
            }
            
        except Exception as e:
            logger.error(f"[MEMORY_HALL] Failed to get summary: {e}")
            return {}

# Singleton
memory_hall = MemoryHall()
