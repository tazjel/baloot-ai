import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import server
sys.path.append(os.getcwd())

# --- MOCKING SETUP BEFORE IMPORTS ---
# We must mock py4web and server.common before importing server.routes.auth
# to avoid database connections or py4web initialization.

mock_py4web = MagicMock()
sys.modules['py4web'] = mock_py4web

# Mock action decorator to be transparent
def action_mock(*args, **kwargs):
    def decorator(f):
        return f
    return decorator
action_mock.uses = lambda *args: lambda f: f
mock_py4web.action = action_mock

# Mock request/response/abort
mock_request = MagicMock()
mock_response = MagicMock()
mock_abort = MagicMock()
mock_py4web.request = mock_request
mock_py4web.response = mock_response
mock_py4web.abort = mock_abort

# Mock server.common
mock_common = MagicMock()
mock_db = MagicMock()
mock_common.db = mock_db
sys.modules['server.common'] = mock_common

# Now we can safely import the module under test
# We also need to make sure auth_utils imports don't fail (it imports server.settings)
# server.settings imports py4web.core... but we mocked py4web.
# Let's hope server.settings works or we mock it too.
# server.auth_utils uses jwt and settings.
try:
    from server.routes.auth import signup, signin
except ImportError as e:
    # If settings fail, we might need to mock server.settings
    print(f"Import failed: {e}")
    sys.modules['server.settings'] = MagicMock()
    sys.modules['server.settings'].SESSION_SECRET_KEY = 'test_secret'
    from server.routes.auth import signup, signin

class TestAuthFlow(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_request.reset_mock()
        mock_response.reset_mock()
        mock_db.reset_mock()
        # Reset request.json
        mock_request.json = {}

    def test_signup_success(self):
        mock_request.json = {
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'valid@example.com',
            'password': 'password123'
        }

        # db(query).select().first() -> None
        mock_set = MagicMock()
        mock_set.select.return_value.first.return_value = None
        mock_db.return_value = mock_set

        mock_db.app_user.insert.return_value = 123

        result = signup()

        self.assertEqual(mock_response.status, 201)
        self.assertEqual(result['email'], 'valid@example.com')
        self.assertEqual(result['user_id'], 123)

        # Verify password hashed
        kwargs = mock_db.app_user.insert.call_args[1]
        self.assertNotEqual(kwargs['password'], 'password123')
        self.assertIsInstance(kwargs['password'], str) # Decoded

    def test_signup_invalid_email(self):
        mock_request.json = {
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'invalid-email',
            'password': 'password123'
        }

        result = signup()
        self.assertEqual(mock_response.status, 400)
        self.assertEqual(result['error'], "Invalid email format")

    def test_signup_short_password(self):
        mock_request.json = {
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'valid@example.com',
            'password': 'short'
        }

        result = signup()
        self.assertEqual(mock_response.status, 400)
        self.assertEqual(result['error'], "Password must be at least 8 characters long")

    def test_signup_missing_fields(self):
        mock_request.json = {
            'firstName': 'Test',
            # lastName missing
            'email': 'valid@example.com',
            'password': 'password123'
        }

        result = signup()
        self.assertEqual(mock_response.status, 400)
        self.assertEqual(result['error'], "All fields are required")

    def test_signup_duplicate_user(self):
        mock_request.json = {
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'exists@example.com',
            'password': 'password123'
        }

        # db(query).select().first() -> User
        mock_user = MagicMock()
        mock_set = MagicMock()
        mock_set.select.return_value.first.return_value = mock_user
        mock_db.return_value = mock_set

        result = signup()
        self.assertEqual(mock_response.status, 409)
        self.assertEqual(result['error'], "User already exists")

    def test_signin_success(self):
        import bcrypt
        mock_request.json = {
            'email': 'valid@example.com',
            'password': 'password123'
        }

        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = 'valid@example.com'
        mock_user.first_name = 'Test'
        mock_user.last_name = 'User'
        mock_user.password = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')

        mock_set = MagicMock()
        mock_set.select.return_value.first.return_value = mock_user
        mock_db.return_value = mock_set

        result = signin()

        self.assertEqual(mock_response.status, 200)
        self.assertIn('token', result)
        self.assertEqual(result['firstName'], 'Test')

    def test_signin_invalid_password(self):
        import bcrypt
        mock_request.json = {
            'email': 'valid@example.com',
            'password': 'WRONGpassword'
        }

        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = 'valid@example.com'
        mock_user.password = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')

        mock_set = MagicMock()
        mock_set.select.return_value.first.return_value = mock_user
        mock_db.return_value = mock_set

        result = signin()

        self.assertIn('error', result)
        self.assertEqual(result['error'], "Invalid credentials")

    def test_signin_user_not_found(self):
        mock_request.json = {
            'email': 'nobody@example.com',
            'password': 'password123'
        }

        mock_set = MagicMock()
        mock_set.select.return_value.first.return_value = None
        mock_db.return_value = mock_set

        result = signin()

        self.assertEqual(mock_response.status, 404)
        self.assertEqual(result['error'], "User not found")

if __name__ == '__main__':
    unittest.main()
