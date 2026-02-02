import time
import threading
import logging

logger = logging.getLogger(__name__)

class TokenBucketRateLimiter:
    """
    Thread-safe Token Bucket Rate Limiter.
    Enforces a strict limit of `refill_rate` requests per minute.
    """
    def __init__(self, capacity: int = 10, refill_rate_per_minute: int = 10):
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_rate = refill_rate_per_minute / 60.0 # tokens per second
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed > 0:
            added_tokens = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + added_tokens)
            self.last_refill = now
            
    def acquire(self, blocking: bool = False) -> bool:
        """
        Attempt to acquire a token.
        Returns True if successful, False otherwise (unless blocking=True, which waits).
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
                
            if not blocking:
                return False
                
        # Blocking logic (simple sleep loop outside lock)
        while True:
            time.sleep(1.0 / self.refill_rate) # Sleep for time to generate 1 token
            with self.lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
                    
    def get_status(self):
        with self.lock:
            self._refill()
            return {
                "tokens": self.tokens,
                "capacity": self.capacity,
                "refill_rate_sec": self.refill_rate
            }

# Singleton instance for Global Limiting
# 10 RPM = 1 request every 6 seconds. Very safe for Free Tier (15 RPM limit).
global_gemini_limiter = TokenBucketRateLimiter(capacity=10, refill_rate_per_minute=10)
