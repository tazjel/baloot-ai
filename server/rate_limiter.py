from __future__ import annotations
import time
from collections import defaultdict

class RateLimiter:
    """
    In-memory Rate Limiter using Sliding Window Log.
    """
    def __init__(self, max_requests: int = 60, window_seconds: int = 60, cleanup_interval: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.cleanup_interval = cleanup_interval
        # Dictionary storing list of timestamps for each client IP
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.last_cleanup = time.time()

    def _cleanup(self):
        """Remove stale entries to prevent memory leaks."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        self.last_cleanup = now
        stale_ips = []
        for ip, timestamps in self.requests.items():
            # If the newest timestamp is older than window, the whole list is stale.
            # We assume timestamps are sorted because we append 'now'.
            if not timestamps or (now - timestamps[-1] > self.window_seconds):
                stale_ips.append(ip)

        for ip in stale_ips:
            del self.requests[ip]

    def check_rate_limit(self, client_ip: str) -> bool:
        """
        Check if the client IP is allowed to make a request.
        :param client_ip: The IP address of the client.
        :return: True if allowed, False if limit exceeded.
        """
        self._cleanup()

        now = time.time()
        # Clean up old timestamps for this IP
        # We keep only timestamps within the current window
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window_seconds]

        # Check limit
        if len(self.requests[client_ip]) >= self.max_requests:
            return False

        # Record new request
        self.requests[client_ip].append(now)
        return True

_limiters: dict[str, RateLimiter] = {}

def get_rate_limiter(name: str = "default") -> RateLimiter:
    """
    Factory function to get or create a named RateLimiter.
    Configures 'auth' limiter with stricter rules (10 req/60s).
    Default limiter is 60 req/60s.
    """
    if name not in _limiters:
        if name == "auth":
            # Stricter limit for auth endpoints
            _limiters[name] = RateLimiter(max_requests=10, window_seconds=60)
        else:
            # Default limit
            _limiters[name] = RateLimiter(max_requests=60, window_seconds=60)
    return _limiters[name]
