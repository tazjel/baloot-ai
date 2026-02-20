"""
Rate limiting for the Baloot AI server.

Provides Redis-based rate limiting with in-memory fallback.
M-MP11: Added get_rate_limiter() factory for named limiter instances.
"""
from __future__ import annotations

import time
import logging
from server.common import redis_client

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based Rate Limiter using Fixed Window Counter.
    Falls back to in-memory counter when Redis is unavailable.
    """
    def __init__(self, key_prefix="rl"):
        self.redis = redis_client
        self.prefix = key_prefix
        # In-memory fallback: {full_key: (count, window_id)}
        self._memory: dict[str, tuple[int, int]] = {}
        self._last_cleanup = time.time()

    def _cleanup_memory(self):
        """Purge expired in-memory entries periodically (every 60s)."""
        now = time.time()
        if now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        # Remove entries older than 2 minutes
        cutoff = int(now) - 120
        stale = [k for k, (_, w) in self._memory.items() if w < cutoff]
        for k in stale:
            del self._memory[k]

    def _check_memory(self, key: str, limit: int, window: int) -> bool:
        """In-memory rate limiter fallback."""
        self._cleanup_memory()
        current_window = int(time.time() // window)
        full_key = f"{self.prefix}:{key}:{current_window}"

        entry = self._memory.get(full_key)
        if entry and entry[1] == current_window:
            count = entry[0] + 1
        else:
            count = 1

        self._memory[full_key] = (count, current_window)

        if count > limit:
            logger.warning(f"Rate Limit Exceeded (memory): {key} ({count}/{limit})")
            return False
        return True

    def check_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Check if an action is allowed.
        :param key: Unique identifier (e.g., user_id or remote_addr)
        :param limit: Max requests allowed in the window
        :param window: Time window in seconds
        :return: True if allowed, False if limit exceeded
        """
        if not self.redis:
            return self._check_memory(key, limit, window)

        # Key specific to the current time window
        # e.g. rl:create_room:127.0.0.1:17000000
        current_window = int(time.time() // window)
        full_key = f"{self.prefix}:{key}:{current_window}"

        try:
            # Atomic INCR
            count = self.redis.incr(full_key)

            # Set expiry on first access
            if count == 1:
                self.redis.expire(full_key, window + 5)  # +5 buffer

            if count > limit:
                logger.warning(f"Rate Limit Exceeded: {key} ({count}/{limit})")
                return False

            return True

        except Exception as e:
            logger.error(f"RateLimiter Redis Error: {e}")
            # Fallback to in-memory instead of failing open
            return self._check_memory(key, limit, window)


# Global Instances for convenience
limiter = RateLimiter()

# Named limiter registry — shared across the process
_named_limiters: dict[str, RateLimiter] = {}


def get_rate_limiter(name: str) -> RateLimiter:
    """Get or create a named RateLimiter instance.

    Named limiters share the same Redis/memory backend but use distinct
    key prefixes so their counters are independent.

    Common names:
        - ``"default"`` — 60 req / 60s (general API)
        - ``"auth"`` — 10 req / 60s (login/signup/refresh)
        - ``"matchmaking"`` — 5 req / 60s (queue operations)

    Args:
        name: Unique name for this limiter category.

    Returns:
        A RateLimiter with ``key_prefix=rl:{name}``.
    """
    if name not in _named_limiters:
        _named_limiters[name] = RateLimiter(key_prefix=f"rl:{name}")
    return _named_limiters[name]
