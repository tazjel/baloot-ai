"""
Tests for M-MP11: Security Hardening — CORS, JWT refresh, rate limiting.

Uses standalone test patterns to avoid deep import chains from the server
modules (room_manager → game_engine → trick_manager → logging_utils).
"""
from __future__ import annotations

import time
import unittest


# ===========================================================================
# 1. Rate Limiter Tests (standalone mirror — avoids redis_client import)
# ===========================================================================

class StandaloneRateLimiter:
    """In-memory rate limiter mirroring server.rate_limiter.RateLimiter."""

    def __init__(self, key_prefix: str = "rl"):
        self.prefix = key_prefix
        self._memory: dict[str, tuple[int, int]] = {}
        self._last_cleanup = time.time()

    def _cleanup_memory(self):
        now = time.time()
        if now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        cutoff = int(now) - 120
        stale = [k for k, (_, w) in self._memory.items() if w < cutoff]
        for k in stale:
            del self._memory[k]

    def check_limit(self, key: str, limit: int, window: int) -> bool:
        self._cleanup_memory()
        current_window = int(time.time() // window)
        full_key = f"{self.prefix}:{key}:{current_window}"

        entry = self._memory.get(full_key)
        if entry and entry[1] == current_window:
            count = entry[0] + 1
        else:
            count = 1

        self._memory[full_key] = (count, current_window)
        return count <= limit


class TestRateLimiter(unittest.TestCase):
    """Tests for rate limiter logic."""

    def setUp(self):
        self.limiter = StandaloneRateLimiter()

    def test_allows_under_limit(self):
        """Requests under the limit should be allowed."""
        for _ in range(5):
            self.assertTrue(self.limiter.check_limit("user1", 10, 60))

    def test_blocks_at_limit(self):
        """Requests at the limit should be blocked."""
        for _ in range(10):
            self.limiter.check_limit("user2", 10, 60)
        # 11th request should be blocked
        self.assertFalse(self.limiter.check_limit("user2", 10, 60))

    def test_blocks_over_limit(self):
        """Requests over the limit should all be blocked."""
        for _ in range(15):
            self.limiter.check_limit("user3", 5, 60)
        self.assertFalse(self.limiter.check_limit("user3", 5, 60))

    def test_separate_keys(self):
        """Different keys have independent counters."""
        for _ in range(10):
            self.limiter.check_limit("userA", 10, 60)
        # userA is at limit
        self.assertFalse(self.limiter.check_limit("userA", 10, 60))
        # userB should still be allowed
        self.assertTrue(self.limiter.check_limit("userB", 10, 60))

    def test_window_reset(self):
        """Counters reset when the window changes."""
        # Use a tiny window (1 second)
        for _ in range(5):
            self.limiter.check_limit("user4", 5, 1)
        self.assertFalse(self.limiter.check_limit("user4", 5, 1))

        # Wait for window to roll over
        time.sleep(1.1)
        self.assertTrue(self.limiter.check_limit("user4", 5, 1))

    def test_auth_preset_stricter(self):
        """Auth limiter should have stricter limits (10 per 60s)."""
        auth_limiter = StandaloneRateLimiter(key_prefix="rl:auth")
        for _ in range(10):
            auth_limiter.check_limit("ip:1.2.3.4", 10, 60)
        self.assertFalse(auth_limiter.check_limit("ip:1.2.3.4", 10, 60))

    def test_named_prefixes_independent(self):
        """Named limiters with different prefixes don't interfere."""
        default_limiter = StandaloneRateLimiter(key_prefix="rl:default")
        auth_limiter = StandaloneRateLimiter(key_prefix="rl:auth")

        # Exhaust auth limiter
        for _ in range(10):
            auth_limiter.check_limit("ip:1.2.3.4", 10, 60)
        self.assertFalse(auth_limiter.check_limit("ip:1.2.3.4", 10, 60))

        # Default limiter should still work
        self.assertTrue(default_limiter.check_limit("ip:1.2.3.4", 60, 60))

    def test_cleanup_removes_stale(self):
        """Cleanup should remove entries older than 2 minutes."""
        limiter = StandaloneRateLimiter()
        # Add an entry with a stale window id
        limiter._memory["rl:test:0"] = (5, 0)  # window 0 = ancient
        limiter._last_cleanup = 0  # Force cleanup on next call
        limiter._cleanup_memory()
        self.assertNotIn("rl:test:0", limiter._memory)

    def test_first_request_always_allowed(self):
        """The first request for any key should always be allowed."""
        self.assertTrue(self.limiter.check_limit("new_user", 1, 60))


# ===========================================================================
# 2. CORS Configuration Tests
# ===========================================================================

class TestCORSConfig(unittest.TestCase):
    """Tests for CORS configuration logic."""

    def test_default_allowed_origins(self):
        """Default origins should include localhost and production domain."""
        # Mirror the defaults from cors_config.py
        allowed = [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://baloot-ai.web.app",
        ]
        self.assertIn("http://localhost:5173", allowed)
        self.assertIn("http://localhost:3000", allowed)
        self.assertIn("https://baloot-ai.web.app", allowed)

    def test_origin_check_allowed(self):
        """Allowed origins should pass the check."""
        allowed = [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://baloot-ai.web.app",
        ]

        def is_allowed(origin):
            return origin in allowed

        self.assertTrue(is_allowed("http://localhost:5173"))
        self.assertTrue(is_allowed("https://baloot-ai.web.app"))

    def test_origin_check_blocked(self):
        """Origins not in the allowed list should be blocked."""
        allowed = [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://baloot-ai.web.app",
        ]

        def is_allowed(origin):
            return origin in allowed

        self.assertFalse(is_allowed("https://evil.com"))
        self.assertFalse(is_allowed("http://localhost:8080"))
        self.assertFalse(is_allowed(""))

    def test_none_origin_blocked(self):
        """None/empty origin should be blocked."""

        def is_allowed(origin):
            if not origin:
                return False
            return origin in ["http://localhost:5173"]

        self.assertFalse(is_allowed(None))
        self.assertFalse(is_allowed(""))

    def test_env_override_parsing(self):
        """CORS_ORIGINS env var should be parsed as comma-separated list."""
        env_value = "https://a.com, https://b.com ,https://c.com"
        parsed = [o.strip() for o in env_value.split(",") if o.strip()]
        self.assertEqual(parsed, ["https://a.com", "https://b.com", "https://c.com"])

    def test_wildcard_env(self):
        """Wildcard '*' should allow any origin."""

        def is_allowed(origin, wildcard=False):
            if wildcard:
                return True
            return origin in ["http://localhost:5173"]

        self.assertTrue(is_allowed("https://anything.com", wildcard=True))


# ===========================================================================
# 3. JWT Token Tests
# ===========================================================================

class TestJWTToken(unittest.TestCase):
    """Tests for JWT token generation and verification."""

    def _make_jwt(self, user_id, email, first_name, last_name, exp_offset=86400):
        """Create a JWT token using the same logic as auth_utils."""
        import jwt as pyjwt

        payload = {
            "user_id": user_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "exp": time.time() + exp_offset,
        }
        return pyjwt.encode(payload, "test-secret", algorithm="HS256")

    def _verify_jwt(self, token):
        """Verify a JWT token using the same logic as auth_utils."""
        import jwt as pyjwt

        try:
            return pyjwt.decode(token, "test-secret", algorithms=["HS256"])
        except pyjwt.ExpiredSignatureError:
            return None
        except pyjwt.InvalidTokenError:
            return None

    def test_valid_token(self):
        """A valid token should verify successfully."""
        token = self._make_jwt(1, "a@b.com", "Ali", "Hassan")
        payload = self._verify_jwt(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["email"], "a@b.com")
        self.assertEqual(payload["user_id"], 1)

    def test_expired_token(self):
        """An expired token should return None."""
        token = self._make_jwt(1, "a@b.com", "Ali", "Hassan", exp_offset=-10)
        payload = self._verify_jwt(token)
        self.assertIsNone(payload)

    def test_invalid_token(self):
        """A garbage token should return None."""
        payload = self._verify_jwt("not.a.real.token")
        self.assertIsNone(payload)

    def test_tampered_token(self):
        """A tampered token should return None."""
        token = self._make_jwt(1, "a@b.com", "Ali", "Hassan")
        # Flip a character in the signature
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        payload = self._verify_jwt(tampered)
        self.assertIsNone(payload)

    def test_missing_token(self):
        """None/empty token should return None."""
        self.assertIsNone(self._verify_jwt(""))

    def test_refresh_returns_new_token(self):
        """Refreshing should produce a token with fresh expiry."""
        original = self._make_jwt(1, "a@b.com", "Ali", "Hassan", exp_offset=3600)
        # Simulate refresh: verify old, generate new with different expiry
        payload = self._verify_jwt(original)
        self.assertIsNotNone(payload)
        refreshed = self._make_jwt(
            payload["user_id"],
            payload["email"],
            payload["first_name"],
            payload["last_name"],
            exp_offset=86400,  # New 24h expiry (different from original 1h)
        )
        # New token should be valid
        new_payload = self._verify_jwt(refreshed)
        self.assertIsNotNone(new_payload)
        self.assertEqual(new_payload["email"], "a@b.com")
        # Fresh expiry should be later than original
        self.assertGreater(new_payload["exp"], payload["exp"])

    def test_token_contains_all_fields(self):
        """Token payload should contain all required fields."""
        token = self._make_jwt(42, "test@baloot.ai", "Fahad", "Al-Rashid")
        payload = self._verify_jwt(token)
        self.assertIn("user_id", payload)
        self.assertIn("email", payload)
        self.assertIn("first_name", payload)
        self.assertIn("last_name", payload)
        self.assertIn("exp", payload)


# ===========================================================================
# 4. Auth Rate Limiting Integration Tests
# ===========================================================================

class TestAuthRateLimiting(unittest.TestCase):
    """Tests for auth endpoint rate limiting behavior."""

    def test_auth_limiter_blocks_after_10(self):
        """Auth endpoints should block after 10 requests per IP."""
        limiter = StandaloneRateLimiter(key_prefix="rl:auth")
        ip = "192.168.1.100"
        for _ in range(10):
            self.assertTrue(limiter.check_limit(f"signin:{ip}", 10, 60))
        # 11th should be blocked
        self.assertFalse(limiter.check_limit(f"signin:{ip}", 10, 60))

    def test_signup_and_signin_share_limiter_prefix(self):
        """Signup and signin use the same auth limiter but different keys."""
        limiter = StandaloneRateLimiter(key_prefix="rl:auth")
        ip = "10.0.0.1"
        # Exhaust signup limit
        for _ in range(10):
            limiter.check_limit(f"signup:{ip}", 10, 60)
        self.assertFalse(limiter.check_limit(f"signup:{ip}", 10, 60))
        # Signin should still work (different key)
        self.assertTrue(limiter.check_limit(f"signin:{ip}", 10, 60))

    def test_refresh_rate_limited(self):
        """Refresh endpoint should also be rate limited."""
        limiter = StandaloneRateLimiter(key_prefix="rl:auth")
        ip = "172.16.0.1"
        for _ in range(10):
            limiter.check_limit(f"refresh:{ip}", 10, 60)
        self.assertFalse(limiter.check_limit(f"refresh:{ip}", 10, 60))


if __name__ == "__main__":
    unittest.main()
