import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import bcrypt

# Ensure we can import server
sys.path.append(os.getcwd())

# We need to setup the DB before importing routes that might use it
# But server.common initializes DB on import.
# We will rely on the fact that we can manipulate the DB object after import
# or that existing DB is fine if we clean up.

from server.common import db
# Ensure models are defined
try:
    from server import models
except ImportError:
    pass

from server.routes import auth

class TestAuth(unittest.TestCase):
    def setUp(self):
        # Clean up app_user table before each test
        if hasattr(db, 'app_user'):
            db.app_user.truncate()

    def test_signup_success(self):
        with patch('server.routes.auth.request') as mock_request, \
             patch('server.routes.auth.response') as mock_response:

            mock_request.json = {
                "firstName": "Test",
                "lastName": "User",
                "email": "test@example.com",
                "password": "password123"
            }

            result = auth.signup()

            self.assertEqual(mock_response.status, 201)
            self.assertEqual(result['email'], "test@example.com")

            # Verify DB
            user = db(db.app_user.email == "test@example.com").select().first()
            self.assertIsNotNone(user)
            self.assertEqual(user.first_name, "Test")
            # Verify default inventory
            self.assertEqual(user.owned_items, ['card_default', 'table_default'])

    def test_signup_duplicate(self):
        # Insert one user
        db.app_user.insert(
            first_name="Existing", last_name="User",
            email="dup@example.com", password=b"pass"
        )

        with patch('server.routes.auth.request') as mock_request, \
             patch('server.routes.auth.response') as mock_response:

            mock_request.json = {
                "firstName": "Test",
                "lastName": "User",
                "email": "dup@example.com",
                "password": "password123"
            }

            result = auth.signup()

            self.assertEqual(mock_response.status, 409)
            self.assertEqual(result['error'], "User already exists")

    def test_signin_success(self):
        hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt())
        user_id = db.app_user.insert(
            first_name="Login",
            last_name="User",
            email="login@example.com",
            password=hashed
        )

        with patch('server.routes.auth.request') as mock_request, \
             patch('server.routes.auth.response') as mock_response:

            mock_request.json = {
                "email": "login@example.com",
                "password": "password123"
            }

            result = auth.signin()

            self.assertEqual(mock_response.status, 200)
            self.assertIn("token", result)
            self.assertEqual(result['firstName'], "Login")

    def test_signin_fail(self):
        with patch('server.routes.auth.request') as mock_request, \
             patch('server.routes.auth.response') as mock_response:

            mock_request.json = {
                "email": "wrong@example.com",
                "password": "pass"
            }

            result = auth.signin()

            self.assertEqual(mock_response.status, 404)
            self.assertEqual(result['error'], "User not found")

    def test_user_profile(self):
        user_id = db.app_user.insert(
            first_name="Profile",
            last_name="User",
            email="profile@example.com",
            password=b"hashed",
            owned_items=["item1"],
            equipped_items={"card": "item1"}
        )

        with patch('server.routes.auth.request') as mock_request, \
             patch('server.routes.auth.response') as mock_response, \
             patch('server.auth_utils.verify_token') as mock_verify:

            # Mock token header
            mock_request.headers.get.return_value = "Bearer mock_token"
            # Mock verification result
            mock_verify.return_value = {'user_id': user_id}

            result = auth.user()

            self.assertEqual(mock_response.status, 200)
            self.assertEqual(result['ownedItems'], ["item1"])
            self.assertEqual(result['equippedItems'], {"card": "item1"})

    def test_update_inventory(self):
        user_id = db.app_user.insert(
            first_name="Inv",
            last_name="User",
            email="inv@example.com",
            password=b"hashed",
            owned_items=[],
            equipped_items={}
        )

        with patch('server.routes.auth.request') as mock_request, \
             patch('server.auth_utils.verify_token') as mock_verify:

            # Mock token header and verification
            mock_request.headers.get.return_value = "Bearer mock_token"
            mock_verify.return_value = {'user_id': user_id}

            mock_request.json = {
                "ownedItems": ["new_item"],
                "equippedItems": {"table": "new_table"}
            }

            result = auth.update_inventory()

            self.assertEqual(result['message'], "Inventory updated")

            user = db.app_user(user_id)
            self.assertEqual(user.owned_items, ["new_item"])
            self.assertEqual(user.equipped_items, {"table": "new_table"})

if __name__ == '__main__':
    unittest.main()
