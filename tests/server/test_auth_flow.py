import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure server module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from server.common import db, auth
from server.routes import auth as auth_routes
from py4web import request, response

def setup_module(module):
    # Ensure clean state
    db.commit()

def teardown_module(module):
    db.rollback()

def test_signup_signin_flow():
    # Cleanup
    db(db.auth_user).delete()
    db.commit()

    email = "test_auth@example.com"
    password = "password123"
    first_name = "Test"
    last_name = "User"

    # Mock request object in auth_routes module
    mock_req = MagicMock()
    # We patch 'server.routes.auth.request' so that the function sees our mock
    with patch('server.routes.auth.request', mock_req):

        # --- Signup ---
        mock_req.json = {
            "email": email,
            "password": password,
            "firstName": first_name,
            "lastName": last_name
        }
        mock_req.method = 'POST'

        res = auth_routes.signup()

        assert response.status == 201 or str(response.status).startswith('201'), f"Signup failed: {res}"
        assert res['email'] == email
        assert 'user_id' in res
        user_id = res['user_id']

        # Verify user in DB
        user = db.auth_user(user_id)
        assert user is not None
        assert user.email == email
        assert user.first_name == first_name
        assert user.league_points == 1000 # default

        # --- Signin ---
        mock_req.json = {
            "email": email,
            "password": password
        }
        res = auth_routes.signin()
        assert response.status == 200 or str(response.status).startswith('200'), f"Signin failed: {res}"
        assert 'token' in res
        token = res['token']

        # --- User (Protected) ---
        mock_req.headers = {'Authorization': f'Bearer {token}'}
        mock_req.method = 'GET'
        # Reset user attribute on mock request as it might be set by decorator
        if hasattr(mock_req, 'user'):
            del mock_req.user

        # token_required decorator uses request.headers to set request.user
        # Since we patched request, the decorator uses our mock_req.
        # But we need to make sure the decorator logic runs.
        # token_required calls auth_utils.verify_token(token)

        res = auth_routes.user()
        assert response.status == 200 or str(response.status).startswith('200')
        assert res['user']['email'] == email
        assert res['leaguePoints'] == 1000
        assert res['tier'] == 'Bronze'

    # Cleanup
    db(db.auth_user).delete()
    db.commit()

def test_signin_invalid_password():
    # Cleanup
    db(db.auth_user).delete()
    db.commit()

    email = "test_invalid@example.com"
    password = "password123"

    # Create user first
    db.auth_user.validate_and_insert(
        email=email,
        password=password,
        first_name="Test",
        last_name="Invalid"
    )
    db.commit()

    mock_req = MagicMock()
    with patch('server.routes.auth.request', mock_req):
        # Try signin with wrong password
        mock_req.json = {
            "email": email,
            "password": "wrongpassword"
        }
        mock_req.method = 'POST'

        res = auth_routes.signin()

        assert 'error' in res
        assert res['error'] == "Invalid credentials"

    # Cleanup
    db(db.auth_user).delete()
    db.commit()
