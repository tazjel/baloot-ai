import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import bcrypt

# Ensure project root is in sys.path
sys.path.append(os.getcwd())

# Mock py4web structure BEFORE imports
mock_py4web = MagicMock()
sys.modules['py4web'] = mock_py4web

# Mock submodules
mock_core = MagicMock()
sys.modules['py4web.core'] = mock_core
mock_py4web.core = mock_core
mock_core.required_folder = lambda *args: "/tmp"

mock_utils = MagicMock()
sys.modules['py4web.utils'] = mock_utils
mock_py4web.utils = mock_utils

mock_downloader = MagicMock()
sys.modules['py4web.utils.downloader'] = mock_downloader
mock_downloader.downloader = MagicMock()

mock_dbstore = MagicMock()
sys.modules['py4web.utils.dbstore'] = mock_dbstore
mock_dbstore.DBStore = MagicMock()

# Setup top level attributes on py4web
mock_py4web.action = MagicMock()
mock_py4web.action.uses = lambda *args: lambda f: f
# Allow action as decorator
mock_py4web.action.side_effect = lambda *args, **kwargs: lambda f: f

mock_request = MagicMock()
mock_response = MagicMock()
mock_py4web.request = mock_request
mock_py4web.response = mock_response
mock_py4web.abort = MagicMock(side_effect=Exception("Abort"))

# Mock DAL, Field, etc
mock_py4web.DAL = MagicMock()
mock_py4web.Field = MagicMock()
mock_py4web.Session = MagicMock()
mock_py4web.Cache = MagicMock()
mock_py4web.Translator = MagicMock()

# Mock server.common
# Since server.common imports py4web, it would be fine, but we want to intercept db
mock_common = MagicMock()
sys.modules['server.common'] = mock_common
mock_db = MagicMock()
mock_common.db = mock_db
# server.common also exports Field
mock_common.Field = MagicMock()

# Now import the module under test
import server.routes.auth as auth

class TestAuth(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_request.reset_mock()
        mock_response.reset_mock()
        mock_db.reset_mock()

        # Default headers
        mock_request.headers = {}
        mock_response.headers = {}

        # Default request method
        mock_request.method = 'POST'

    def test_signup_success(self):
        mock_request.json = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "password": "password123"
        }

        # Mock no existing user
        mock_set = MagicMock()
        mock_db.side_effect = lambda *args: mock_set
        mock_set.select.return_value.first.return_value = None

        # Mock insert
        mock_db.app_user.insert.return_value = 1

        result = auth.signup()

        self.assertEqual(mock_response.status, 201)
        self.assertEqual(result['email'], "john@example.com")
        mock_db.app_user.insert.assert_called_once()

    def test_signup_invalid_email(self):
        mock_request.json = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "invalid-email",
            "password": "password123"
        }

        result = auth.signup()
        self.assertEqual(mock_response.status, 400)
        self.assertEqual(result['error'], "Invalid email address")

    def test_signup_existing_user(self):
        mock_request.json = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "password": "password123"
        }

        mock_set = MagicMock()
        mock_db.side_effect = lambda *args: mock_set
        mock_set.select.return_value.first.return_value = {"id": 1}

        result = auth.signup()

        self.assertEqual(mock_response.status, 409)
        self.assertEqual(result['error'], "User already exists")
        mock_db.app_user.insert.assert_not_called()

    def test_signin_success(self):
        mock_request.json = {
            "email": "john@example.com",
            "password": "password123"
        }

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "john@example.com"
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"
        hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode('utf-8')
        mock_user.password = hashed

        mock_set = MagicMock()
        mock_db.side_effect = lambda *args: mock_set
        mock_set.select.return_value.first.return_value = mock_user

        with patch('server.auth_utils.generate_token', return_value="fake_token"):
            result = auth.signin()

        self.assertEqual(mock_response.status, 200)
        self.assertEqual(result['token'], "fake_token")

    def test_update_profile(self):
        mock_request.json = {
            "firstName": "Jane",
            "lastName": "Doe"
        }
        mock_request.method = 'PUT'
        mock_request.headers = {'Authorization': 'Bearer fake_token'}

        mock_user_record = MagicMock()
        mock_db.app_user.return_value = mock_user_record

        with patch('server.auth_utils.verify_token', return_value={"user_id": 1}):
            result = auth.update_profile()

        mock_user_record.update_record.assert_called_with(first_name="Jane", last_name="Doe")
        self.assertEqual(result['firstName'], "Jane")

    def test_change_password(self):
        mock_request.json = {
            "currentPassword": "password123",
            "newPassword": "newpassword123"
        }
        mock_request.method = 'POST'
        mock_request.headers = {'Authorization': 'Bearer fake_token'}

        mock_user_record = MagicMock()
        hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode('utf-8')
        mock_user_record.password = hashed
        mock_db.app_user.return_value = mock_user_record

        with patch('server.auth_utils.verify_token', return_value={"user_id": 1}):
            result = auth.change_password()

        self.assertEqual(result['message'], "Password changed successfully")

        args, kwargs = mock_user_record.update_record.call_args
        self.assertTrue(bcrypt.checkpw(b"newpassword123", kwargs['password']))

if __name__ == '__main__':
    unittest.main()
