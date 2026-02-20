"""Integration tests for auth endpoints (M-MP9).

Covers signup, signin, and token validation flows.
Uses isolated mock setup that doesn't contaminate test_stats_api.py.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import importlib

# ──────────────────────────────────────────────────────────────────────
# Setup mocks for auth module (these are independent of stats mocks).
# We force-reload the auth module with fresh mocks to avoid contamination.
# ──────────────────────────────────────────────────────────────────────

_mock_action = MagicMock()
_mock_action.uses.side_effect = lambda *args: lambda f: f
_mock_action.side_effect = lambda *args, **kwargs: lambda f: f

_mock_request = MagicMock()
_mock_response = MagicMock()
_mock_abort = MagicMock()
_mock_db = MagicMock()

# Ensure py4web mock is set (setdefault won't overwrite existing)
if 'py4web' not in sys.modules:
    sys.modules['py4web'] = MagicMock()

# Mock bcrypt
_mock_bcrypt = MagicMock()
_mock_bcrypt.hashpw.return_value = b'$2b$12$hashedpassword'
_mock_bcrypt.checkpw.return_value = True
_mock_bcrypt.gensalt.return_value = b'$2b$12$salt'
sys.modules['bcrypt'] = _mock_bcrypt

# Mock auth_utils
_mock_auth_utils = MagicMock()
_mock_auth_utils.generate_token.return_value = 'mock_jwt_token_123'
_mock_auth_utils.verify_token.return_value = {'user_id': 1, 'email': 'test@example.com'}
sys.modules['server.auth_utils'] = _mock_auth_utils

# Ensure server.common is set
if 'server.common' not in sys.modules:
    _mock_common = MagicMock()
    _mock_common.db = _mock_db
    sys.modules['server.common'] = _mock_common


class TestSignup(unittest.TestCase):
    """Tests for POST /signup."""

    def setUp(self):
        # Patch the module-level names directly on the auth module
        self.db_patcher = patch('server.routes.auth.db')
        self.req_patcher = patch('server.routes.auth.request')
        self.res_patcher = patch('server.routes.auth.response')
        self.bcrypt_patcher = patch('server.routes.auth.bcrypt')

        self.mock_db = self.db_patcher.start()
        self.mock_request = self.req_patcher.start()
        self.mock_response = self.res_patcher.start()
        self.mock_bcrypt = self.bcrypt_patcher.start()

        self.mock_bcrypt.hashpw.return_value = b'$2b$12$hashed'
        self.mock_bcrypt.gensalt.return_value = b'$2b$12$salt'
        self.mock_response.status = 200

    def tearDown(self):
        self.db_patcher.stop()
        self.req_patcher.stop()
        self.res_patcher.stop()
        self.bcrypt_patcher.stop()

    def test_signup_success(self):
        """Signup with valid data returns 201."""
        from server.routes.auth import signup
        self.mock_request.json = {
            'firstName': 'Ali', 'lastName': 'M',
            'email': 'ali@test.com', 'password': 'pass123',
        }
        self.mock_db.return_value.select.return_value.first.return_value = None
        self.mock_db.app_user.insert.return_value = 42

        result = signup()
        self.assertEqual(self.mock_response.status, 201)
        self.assertEqual(result['email'], 'ali@test.com')
        self.assertEqual(result['user_id'], 42)

    def test_signup_duplicate_email(self):
        """Signup with existing email returns 409."""
        from server.routes.auth import signup
        self.mock_request.json = {
            'firstName': 'Ali', 'lastName': 'M',
            'email': 'dup@test.com', 'password': 'pass123',
        }
        self.mock_db.return_value.select.return_value.first.return_value = MagicMock()

        result = signup()
        self.assertEqual(self.mock_response.status, 409)
        self.assertIn('error', result)

    def test_signup_returns_correct_fields(self):
        """Signup response includes required fields."""
        from server.routes.auth import signup
        self.mock_request.json = {
            'firstName': 'Sara', 'lastName': 'A',
            'email': 'sara@test.com', 'password': 'pass123',
        }
        self.mock_db.return_value.select.return_value.first.return_value = None
        self.mock_db.app_user.insert.return_value = 10

        result = signup()
        for key in ('email', 'firstName', 'lastName', 'user_id'):
            self.assertIn(key, result)


class TestSignin(unittest.TestCase):
    """Tests for POST /signin."""

    def setUp(self):
        self.db_patcher = patch('server.routes.auth.db')
        self.req_patcher = patch('server.routes.auth.request')
        self.res_patcher = patch('server.routes.auth.response')
        self.bcrypt_patcher = patch('server.routes.auth.bcrypt')
        self.auth_patcher = patch('server.routes.auth.auth_utils')

        self.mock_db = self.db_patcher.start()
        self.mock_request = self.req_patcher.start()
        self.mock_response = self.res_patcher.start()
        self.mock_bcrypt = self.bcrypt_patcher.start()
        self.mock_auth = self.auth_patcher.start()

        self.mock_bcrypt.checkpw.return_value = True
        self.mock_auth.generate_token.return_value = 'jwt_token_abc'
        self.mock_response.status = 200

    def tearDown(self):
        self.db_patcher.stop()
        self.req_patcher.stop()
        self.res_patcher.stop()
        self.bcrypt_patcher.stop()
        self.auth_patcher.stop()

    def test_signin_success_returns_token(self):
        """Signin with valid credentials returns JWT token."""
        from server.routes.auth import signin
        self.mock_request.json = {'email': 'ali@test.com', 'password': 'pass123'}
        user_record = MagicMock()
        user_record.id = 1
        user_record.email = 'ali@test.com'
        user_record.first_name = 'Ali'
        user_record.last_name = 'M'
        user_record.password = '$2b$12$hashed'
        self.mock_db.return_value.select.return_value.first.return_value = user_record

        result = signin()
        self.assertIn('token', result)
        self.assertEqual(result['token'], 'jwt_token_abc')

    def test_signin_user_not_found(self):
        """Signin with non-existent email returns 404."""
        from server.routes.auth import signin
        self.mock_request.json = {'email': 'nobody@test.com', 'password': 'x'}
        self.mock_db.return_value.select.return_value.first.return_value = None

        result = signin()
        self.assertEqual(self.mock_response.status, 404)
        self.assertIn('error', result)

    def test_signin_wrong_password(self):
        """Signin with wrong password returns error."""
        from server.routes.auth import signin
        self.mock_request.json = {'email': 'ali@test.com', 'password': 'wrong'}
        user_record = MagicMock()
        user_record.password = '$2b$12$hashed'
        self.mock_db.return_value.select.return_value.first.return_value = user_record
        self.mock_bcrypt.checkpw.return_value = False

        result = signin()
        self.assertIn('error', result)

    def test_signin_missing_email(self):
        """Signin without email returns error."""
        from server.routes.auth import signin
        self.mock_request.json = {'password': 'pass123'}
        result = signin()
        self.assertIn('error', result)

    def test_signin_missing_password(self):
        """Signin without password returns error."""
        from server.routes.auth import signin
        self.mock_request.json = {'email': 'ali@test.com'}
        result = signin()
        self.assertIn('error', result)

    def test_signin_returns_user_info(self):
        """Successful signin returns email and name."""
        from server.routes.auth import signin
        self.mock_request.json = {'email': 'ali@test.com', 'password': 'pass'}
        user_record = MagicMock()
        user_record.id = 1
        user_record.email = 'ali@test.com'
        user_record.first_name = 'Ali'
        user_record.last_name = 'M'
        user_record.password = '$2b$12$hashed'
        self.mock_db.return_value.select.return_value.first.return_value = user_record

        result = signin()
        self.assertEqual(result['email'], 'ali@test.com')
        self.assertEqual(result['firstName'], 'Ali')


class TestUserEndpoint(unittest.TestCase):
    """Tests for GET /user (protected endpoint)."""

    def setUp(self):
        self.db_patcher = patch('server.routes.auth.db')
        self.req_patcher = patch('server.routes.auth.request')
        self.res_patcher = patch('server.routes.auth.response')

        self.mock_db = self.db_patcher.start()
        self.mock_request = self.req_patcher.start()
        self.mock_response = self.res_patcher.start()
        self.mock_response.status = 200

    def tearDown(self):
        self.db_patcher.stop()
        self.req_patcher.stop()
        self.res_patcher.stop()

    def test_user_returns_league_info(self):
        """GET /user returns leaguePoints and tier."""
        from server.routes.auth import user
        self.mock_request.user = {'user_id': 1, 'email': 'test@example.com'}
        user_record = MagicMock()
        user_record.league_points = 1500
        self.mock_db.app_user.return_value = user_record

        result = user()
        self.assertIn('leaguePoints', result)
        self.assertIn('tier', result)

    def test_user_tier_grandmaster(self):
        """2000+ points = Grandmaster tier."""
        from server.routes.auth import user
        self.mock_request.user = {'user_id': 1}
        user_record = MagicMock()
        user_record.league_points = 2100
        self.mock_db.app_user.return_value = user_record

        result = user()
        self.assertEqual(result['tier'], 'Grandmaster')

    def test_user_no_record_defaults(self):
        """Missing user record defaults to 1000 points."""
        from server.routes.auth import user
        self.mock_request.user = {'user_id': 999}
        self.mock_db.app_user.return_value = None

        result = user()
        self.assertEqual(result['leaguePoints'], 1000)


if __name__ == '__main__':
    unittest.main()
