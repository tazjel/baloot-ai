import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from server.common import db, auth

class TestAuthFlow(unittest.TestCase):
    def setUp(self):
        # Clean up user if exists
        db(db.auth_user.email == 'test@example.com').delete()
        db.commit()

    def tearDown(self):
        db(db.auth_user.email == 'test@example.com').delete()
        db.commit()

    def test_auth_setup_and_login(self):
        # 1. Register User directly via DB (simulating what signup does)
        result = db.auth_user.validate_and_insert(
            first_name='Test',
            last_name='User',
            email='test@example.com',
            password='password123'
        )

        # Check result
        if hasattr(result, 'errors') and result.errors:
             self.fail(f"Registration failed: {result.errors}")
        elif isinstance(result, dict) and 'errors' in result and result['errors']:
             self.fail(f"Registration failed: {result['errors']}")

        # In this environment, validate_and_insert returns a dict
        user_id = result.get('id')
        self.assertIsNotNone(user_id)
        db.commit() # Commit changes

        # 2. Verify league_points default
        user = db.auth_user(user_id)
        self.assertEqual(user.league_points, 1000)

        # 3. Verify Password Hashing (should not be plaintext)
        self.assertNotEqual(user.password, 'password123')

        # 4. Verify Login Logic
        logged_in_user, error = auth.login('test@example.com', 'password123')
        self.assertIsNotNone(logged_in_user)
        self.assertIsNone(error)
        self.assertEqual(logged_in_user['id'], user_id)

        # 5. Verify Bad Password
        bad_user, error = auth.login('test@example.com', 'wrongpass')
        self.assertIsNone(bad_user)
        self.assertIsNotNone(error)

if __name__ == '__main__':
    unittest.main()
