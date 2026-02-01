import unittest
from unittest.mock import MagicMock, patch
import time
from server.rate_limiter import RateLimiter

class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        # Mock the redis client within the RateLimiter instance
        self.mock_redis = MagicMock()
        self.limiter = RateLimiter(key_prefix="test_rl")
        self.limiter.redis = self.mock_redis

    def test_basic_limiting_logic(self):
        """Test that it allows N requests and blocks N+1 using Mock"""
        key = "user_1"
        limit = 5
        window = 60
        
        # Scenario: Redis INCR returns 1, 2, 3, 4, 5 (Allowed)
        # Then 6 (Blocked)
        
        # We simulate 6 calls
        # check_limit calls redis.incr
        self.mock_redis.incr.side_effect = [1, 2, 3, 4, 5, 6]
        
        # First 5 should match limit
        for i in range(5):
            allowed = self.limiter.check_limit(key, limit, window)
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
            
        # 6th should fail
        allowed = self.limiter.check_limit(key, limit, window)
        self.assertFalse(allowed, "Request 6 should be blocked")
        
        # Verify INCR was called with correct key format
        # Key format: prefix:key:window_integer
        # We don't check the exact window integer as it depends on time, but we check prefix
        args, _ = self.mock_redis.incr.call_args
        self.assertTrue(args[0].startswith("test_rl:user_1:"), f"Bad key format: {args[0]}")

    def test_fail_open_on_redis_error(self):
        """Test that it returns True (Allowed) if Redis raises exception"""
        self.mock_redis.incr.side_effect = Exception("Connection Down")
        
        allowed = self.limiter.check_limit("user_x", 5, 60)
        self.assertTrue(allowed, "Should fail open (True) on redis error")

    def test_expiry_set_on_first_incr(self):
        """Test that EXPIRE is called when count is 1"""
        self.mock_redis.incr.return_value = 1
        
        self.limiter.check_limit("user_y", 5, 60)
        
        # Verify expire called
        self.mock_redis.expire.assert_called_once()
        args, _ = self.mock_redis.expire.call_args
        self.assertEqual(args[1], 65) # window + 5

    def test_expiry_not_set_on_subsequent_incr(self):
        """Test that EXPIRE is NOT called when count > 1"""
        self.mock_redis.incr.return_value = 2
        
        self.limiter.check_limit("user_z", 5, 60)
        
        self.mock_redis.expire.assert_not_called()

if __name__ == '__main__':
    unittest.main()
