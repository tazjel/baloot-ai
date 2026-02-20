"""
Authentication routes: signup, signin, user profile, token refresh, token_required decorator.

M-MP11: Added /auth/refresh endpoint and auth rate limiting.
"""
from __future__ import annotations

import bcrypt
import logging
from py4web import action, request, response, abort
from server.common import db
import server.auth_utils as auth_utils
from server.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

# Stricter rate limiter for auth endpoints: 10 req / 60s per IP
_auth_limiter = get_rate_limiter("auth")


def token_required(f):
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            abort(401, 'Authorization token is missing or invalid')

        token = auth_header.split(" ")[1]

        payload = auth_utils.verify_token(token)
        if not payload:
            abort(401, 'Invalid or Expired Token')

        request.user = payload
        return f(*args, **kwargs)

    return decorated


def validate_password(password):
    """Enforce password complexity rules."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    return True, None


@action('user', method=['GET'])
@token_required
def user():
    """Protected endpoint returning user profile with league tier."""
    response.status = 200
    user_record = db.app_user(request.user.get('user_id'))
    points = user_record.league_points if user_record else 1000
    membership_tier = user_record.membership_tier if user_record and 'membership_tier' in user_record else 'free'

    tier = "Bronze"
    if points >= 2000: tier = "Grandmaster"
    elif points >= 1800: tier = "Diamond"
    elif points >= 1600: tier = "Platinum"
    elif points >= 1400: tier = "Gold"
    elif points >= 1200: tier = "Silver"

    return {
        "user": request.user,
        "leaguePoints": points,
        "tier": tier,
        "membershipTier": membership_tier
    }


@action('signup', method=['POST', 'OPTIONS'])
@action.uses(db)
def signup():
    # Rate limit auth endpoints (10 req / 60s per IP)
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    if not _auth_limiter.check_limit(f"signup:{client_ip}", 10, 60):
        response.status = 429
        return {"error": "Too many requests. Please try again later."}

    data = request.json
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    password = data.get('password')
    email = data.get('email')

    # Validation
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        response.status = 400
        return {"error": error_msg}

    logger.info(f"{email} is signing up!")

    existing_user = db(db.app_user.email == email).select().first()
    if existing_user:
        response.status = 409
        return {"error": "User already exists"}

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    user_id = db.app_user.insert(
        first_name=first_name, last_name=last_name,
        email=email, password=hashed_password
    )

    response.status = 201
    return {
        "message": "User registered successfully",
        "email": email, "firstName": first_name,
        "lastName": last_name, "user_id": user_id
    }


@action('signin', method=['POST'])
def signin():
    # Rate limit auth endpoints (10 req / 60s per IP)
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    if not _auth_limiter.check_limit(f"signin:{client_ip}", 10, 60):
        response.status = 429
        return {"error": "Too many requests. Please try again later."}

    data = request.json
    email = data.get('email')
    password = data.get('password')

    logger.info("User is signing in!")

    if not email or not password:
        return {"error": "Email and password are required"}

    user = db(db.app_user.email == email).select().first()

    if not user:
        logger.warning(f"Sign-in failed: user not found ({email})")
        response.status = 404
        return {"error": "User not found"}

    if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        token = auth_utils.generate_token(user.id, user.email, user.first_name, user.last_name)
        response.status = 200
        return {"email": user.email, "firstName": user.first_name, "lastName": user.last_name, "token": token}

    return {"error": "Invalid credentials"}


@action('refresh', method=['POST'])
@token_required
def refresh():
    """Refresh a valid JWT token — returns a new token with 24h expiry.

    Requires a valid (non-expired) Bearer token in the Authorization header.
    Returns 401 if the token is missing, invalid, or expired.
    """
    # Rate limit refresh endpoint
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    if not _auth_limiter.check_limit(f"refresh:{client_ip}", 10, 60):
        response.status = 429
        return {"error": "Too many requests. Please try again later."}

    user_payload = request.user
    new_token = auth_utils.generate_token(
        user_payload.get('user_id'),
        user_payload.get('email'),
        user_payload.get('first_name'),
        user_payload.get('last_name'),
    )

    response.status = 200
    return {"token": new_token, "message": "Token refreshed successfully"}


def bind_auth(safe_mount):
    """Bind auth routes to the app."""
    safe_mount('/user', 'GET', user)
    safe_mount('/signup', 'POST', signup)
    safe_mount('/signup', 'OPTIONS', signup)
    safe_mount('/signin', 'POST', signin)
    safe_mount('/auth/refresh', 'POST', refresh)
