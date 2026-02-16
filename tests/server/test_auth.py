import pytest
import bcrypt
import json
from unittest.mock import MagicMock, patch
from server.common import db
# Ensure models are loaded
import server.models
from server.routes import auth

# Setup database for tests
@pytest.fixture(autouse=True)
def setup_db():
    try:
        db.app_user.truncate()
    except Exception:
        pass
    yield
    try:
        db.app_user.truncate()
    except Exception:
        pass

def test_signup_success():
    with patch('server.routes.auth.request') as mock_request, \
         patch('server.routes.auth.response') as mock_response:

        mock_request.json = {
            "firstName": "Test",
            "lastName": "User",
            "email": "test@example.com",
            "password": "password123"
        }

        result = auth.signup()

        assert mock_response.status == 201
        assert result['email'] == "test@example.com"

        user = db(db.app_user.email == "test@example.com").select().first()
        assert user is not None
        assert user.first_name == "Test"
        # Verify password is hashed and stored as string (decoded)
        assert isinstance(user.password, str)
        assert user.password != "password123"
        # If it was stored as bytes, checking it as string might fail if not decoded properly
        # We expect it to be a valid bcrypt hash string
        assert user.password.startswith('$2b$') or user.password.startswith('$2a$')
        assert bcrypt.checkpw("password123".encode('utf-8'), user.password.encode('utf-8'))

def test_signup_duplicate_email():
    # Insert existing user
    hashed = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.app_user.insert(
        first_name="Existing",
        last_name="User",
        email="existing@example.com",
        password=hashed
    )

    with patch('server.routes.auth.request') as mock_request, \
         patch('server.routes.auth.response') as mock_response:

        mock_request.json = {
            "firstName": "New",
            "lastName": "User",
            "email": "existing@example.com",
            "password": "newpassword"
        }

        result = auth.signup()

        assert mock_response.status == 409
        assert "User already exists" in result['error']

def test_signin_success():
    # Insert user
    hashed = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.app_user.insert(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password=hashed
    )

    with patch('server.routes.auth.request') as mock_request, \
         patch('server.routes.auth.response') as mock_response:

        mock_request.json = {
            "email": "test@example.com",
            "password": "password123"
        }

        result = auth.signin()

        assert mock_response.status == 200
        assert "token" in result
        assert result['email'] == "test@example.com"

def test_signin_wrong_password():
    # Insert user
    hashed = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.app_user.insert(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password=hashed
    )

    with patch('server.routes.auth.request') as mock_request, \
         patch('server.routes.auth.response') as mock_response:

        mock_request.json = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }

        result = auth.signin()

        assert "error" in result
        assert result["error"] == "Invalid credentials"

def test_signin_user_not_found():
    with patch('server.routes.auth.request') as mock_request, \
         patch('server.routes.auth.response') as mock_response:

        mock_request.json = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }

        result = auth.signin()

        assert mock_response.status == 404
        assert "error" in result

def test_update_profile():
    # Insert user
    hashed = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = db.app_user.insert(
        first_name="Old",
        last_name="Name",
        email="update@example.com",
        password=hashed
    )

    with patch('server.routes.auth.request') as mock_request, \
         patch('server.routes.auth.response') as mock_response, \
         patch('server.auth_utils.verify_token') as mock_verify:

        # Mock auth token verification
        mock_request.headers.get.return_value = "Bearer validtoken"
        mock_verify.return_value = {"user_id": user_id, "email": "update@example.com"}

        mock_request.json = {
            "firstName": "NewName"
        }

        result = auth.update_profile()

        assert result['firstName'] == "NewName"
        assert result['lastName'] == "Name"

        user = db.app_user(user_id)
        assert user.first_name == "NewName"

def test_change_password_success():
    # Insert user
    hashed = bcrypt.hashpw("oldpassword".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = db.app_user.insert(
        first_name="Test",
        last_name="User",
        email="changepw@example.com",
        password=hashed
    )

    with patch('server.routes.auth.request') as mock_request, \
         patch('server.routes.auth.response') as mock_response, \
         patch('server.auth_utils.verify_token') as mock_verify:

        mock_request.headers.get.return_value = "Bearer validtoken"
        mock_verify.return_value = {"user_id": user_id}

        mock_request.json = {
            "oldPassword": "oldpassword",
            "newPassword": "newpassword123"
        }

        result = auth.change_password()

        assert "message" in result

        user = db.app_user(user_id)
        assert bcrypt.checkpw("newpassword123".encode('utf-8'), user.password.encode('utf-8'))

def test_change_password_wrong_old():
    # Insert user
    hashed = bcrypt.hashpw("oldpassword".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = db.app_user.insert(
        first_name="Test",
        last_name="User",
        email="wrongold@example.com",
        password=hashed
    )

    with patch('server.routes.auth.request') as mock_request, \
         patch('server.routes.auth.response') as mock_response, \
         patch('server.auth_utils.verify_token') as mock_verify:

        mock_request.headers.get.return_value = "Bearer validtoken"
        mock_verify.return_value = {"user_id": user_id}

        mock_request.json = {
            "oldPassword": "wrongpassword",
            "newPassword": "newpassword123"
        }

        result = auth.change_password()

        assert mock_response.status == 401
        assert "error" in result
