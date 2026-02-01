import time
import logging
from server.common import redis_client

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Simple Redis-based Rate Limiter using Fixed Window Counter.
    Fails OPEN (allows request) if Redis is unavailable.
    """
    def __init__(self, key_prefix="rl"):
        self.redis = redis_client
        self.prefix = key_prefix

    def check_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Check if an action is allowed.
        :param key: Unique identifier (e.g., user_id or remote_addr)
        :param limit: Max requests allowed in the window
        :param window: Time window in seconds
        :return: True if allowed, False if limit exceeded
        """
        if not self.redis: 
            return True 
        
        # Key specific to the current time window
        # e.g. rl:create_room:127.0.0.1:17000000
        current_window = int(time.time() // window)
        full_key = f"{self.prefix}:{key}:{current_window}"
        
        try:
            # Atomic INCR
            count = self.redis.incr(full_key)
            
            # Set expiry on first access
            if count == 1:
                self.redis.expire(full_key, window + 5) # +5 buffer
            
            if count > limit:
                logger.warning(f"Rate Limit Exceeded: {key} ({count}/{limit})")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"RateLimiter Error: {e}")
            return True # Fail open to ensure availability

# Global Instances for convenience
limiter = RateLimiter()
