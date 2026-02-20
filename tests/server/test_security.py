from __future__ import annotations
import unittest
from unittest.mock import MagicMock, patch
import sys
import time

# --- MOCKING DEPENDENCIES BEFORE IMPORT ---
# We need to mock sys.modules for server.common and server.auth_utils
# because server.routes.auth imports them at top level.

mock_common = MagicMock()
mock_db = MagicMock()
mock_common.db = mock_db
sys.modules['server.common'] = mock_common

mock_auth_utils = MagicMock()
sys.modules['server.auth_utils'] = mock_auth_utils

# Mock bcrypt
sys.modules['bcrypt'] = MagicMock()

# Mock py4web
mock_py4web = MagicMock()
mock_request = MagicMock()
mock_response = MagicMock()
mock_abort = MagicMock()

mock_py4web.request = mock_request
mock_py4web.response = mock_response
mock_py4web.abort = mock_abort

# Mock action decorator
def mock_action(*args, **kwargs):
    def decorator(f):
        return f
    return decorator
mock_action.uses = lambda *args, **kwargs: lambda f: f
mock_py4web.action = mock_action

sys.modules['py4web'] = mock_py4web
sys.modules['py4web.core'] = MagicMock()
sys.modules['py4web.core'].bottle = MagicMock()

# --- IMPORTS ---
from server.rate_limiter import RateLimiter, get_rate_limiter
from server.cors_config import configure_cors, ALLOWED_ORIGINS
import server.routes.auth as auth_routes

class TestSecurity(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_request.reset_mock()
        mock_response.reset_mock()
        mock_abort.reset_mock()
        mock_auth_utils.reset_mock()

        # Reset rate limiters
        auth_routes.auth_limiter.requests.clear()

        # Setup default response headers mock
        mock_response.headers = {}

    def test_rate_limiter_logic(self):
        """Test the in-memory rate limiter logic."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        ip = "192.168.1.1"

        # First 2 requests allowed
        self.assertTrue(limiter.check_rate_limit(ip))
        self.assertTrue(limiter.check_rate_limit(ip))

        # 3rd request blocked
        self.assertFalse(limiter.check_rate_limit(ip))

        # Wait for window to pass
        time.sleep(1.1)

        # Request allowed again
        self.assertTrue(limiter.check_rate_limit(ip))

    def test_auth_rate_limiting_enforcement(self):
        """Test that auth endpoints enforce stricter rate limits."""
        mock_request.remote_addr = "10.0.0.1"

        # Auth limit is 10 per 60s
        for _ in range(10):
            auth_routes.check_auth_rate_limit()

        # 11th request should trigger abort(429)
        mock_abort.side_effect = Exception("Too Many Requests")

        with self.assertRaises(Exception) as cm:
            auth_routes.check_auth_rate_limit()

        self.assertEqual(str(cm.exception), "Too Many Requests")
        mock_abort.assert_called_with(429, "Too Many Requests")
        mock_abort.side_effect = None

    def test_refresh_endpoint_success(self):
        """Test successful token refresh."""
        # Setup
        mock_request.remote_addr = "10.0.0.2"
        mock_request.headers = {'Authorization': 'Bearer valid_token'}

        user_payload = {
            'user_id': 123,
            'email': 'test@test.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
        mock_auth_utils.verify_token.return_value = user_payload
        mock_auth_utils.generate_token.return_value = "new_refreshed_token"

        # Execute
        result = auth_routes.refresh()

        # Verify
        self.assertEqual(result, {"token": "new_refreshed_token"})
        mock_auth_utils.verify_token.assert_called_with("valid_token")
        mock_auth_utils.generate_token.assert_called_with(
            123, 'test@test.com', 'Test', 'User'
        )

    def test_refresh_endpoint_expired_token(self):
        """Test refresh with expired/invalid token."""
        mock_request.remote_addr = "10.0.0.3"
        mock_request.headers = {'Authorization': 'Bearer expired_token'}

        mock_auth_utils.verify_token.return_value = None # Simulating expiration

        mock_abort.side_effect = Exception("Unauthorized")

        with self.assertRaises(Exception):
            auth_routes.refresh()

        mock_abort.assert_called_with(401, 'Invalid or Expired Token')
        mock_abort.side_effect = None

    def test_cors_configuration(self):
        """Test CORS configuration and header generation."""
        mock_app = MagicMock()
        configure_cors(mock_app)

        # Check if hook was registered
        mock_app.hook.assert_called_with('after_request')

        # Get the inner function 'enable_cors'
        # app.hook('after_request') returns a decorator, which is called with enable_cors
        decorator = mock_app.hook.return_value
        enable_cors_func = decorator.call_args[0][0]

        # Test allowed origin
        allowed_origin = ALLOWED_ORIGINS[0]
        mock_request.headers = {'Origin': allowed_origin}
        mock_response.headers = {}

        enable_cors_func()

        self.assertEqual(mock_response.headers['Access-Control-Allow-Origin'], allowed_origin)
        self.assertEqual(mock_response.headers['Access-Control-Allow-Credentials'], 'true')

        # Test disallowed origin
        mock_request.headers = {'Origin': 'http://evil.com'}
        mock_response.headers = {}

        enable_cors_func()

        self.assertNotIn('Access-Control-Allow-Origin', mock_response.headers)

    def test_rate_limiter_cleanup(self):
        """Test that stale entries are cleaned up."""
        # Create limiter with short window and cleanup interval
        limiter = RateLimiter(max_requests=10, window_seconds=0.1, cleanup_interval=0.1)

        # Add entry
        limiter.check_rate_limit("1.1.1.1")
        self.assertIn("1.1.1.1", limiter.requests)

        # Wait for expiration
        time.sleep(0.2)

        # Trigger check with another IP to trigger cleanup
        limiter.check_rate_limit("2.2.2.2")

        # Check if 1.1.1.1 is removed
        self.assertNotIn("1.1.1.1", limiter.requests)
        self.assertIn("2.2.2.2", limiter.requests)

if __name__ == '__main__':
    unittest.main()
