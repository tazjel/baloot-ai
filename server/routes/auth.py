"""
Authentication routes: signup, signin, user profile, token_required decorator.
"""
import bcrypt
import logging
import re
from py4web import action, request, response, abort
from server.common import db
import server.auth_utils as auth_utils

logger = logging.getLogger(__name__)


def enable_cors(f):
    def decorated(*args, **kwargs):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
        if request.method == 'OPTIONS':
            return ""
        return f(*args, **kwargs)
    return decorated


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


@action('user', method=['GET', 'OPTIONS'])
@enable_cors
@token_required
def user():
    """Protected endpoint returning user profile with league tier."""
    response.status = 200
    user_record = db.app_user(request.user.get('user_id'))
    points = user_record.league_points if user_record else 1000

    tier = "Bronze"
    if points >= 2000: tier = "Grandmaster"
    elif points >= 1800: tier = "Diamond"
    elif points >= 1600: tier = "Platinum"
    elif points >= 1400: tier = "Gold"
    elif points >= 1200: tier = "Silver"

    return {"user": request.user, "leaguePoints": points, "tier": tier}


@action('signup', method=['POST', 'OPTIONS'])
@action.uses(db)
@enable_cors
def signup():
    data = request.json
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    password = data.get('password')
    email = data.get('email')

    if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        response.status = 400
        return {"error": "Invalid email address"}

    if not password or len(password) < 6:
        response.status = 400
        return {"error": "Password must be at least 6 characters"}

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


@action('signin', method=['POST', 'OPTIONS'])
@enable_cors
@action.uses(db)
def signin():
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


@action('user', method=['PUT', 'OPTIONS'])
@enable_cors
@token_required
@action.uses(db)
def update_profile():
    data = request.json
    first_name = data.get('firstName')
    last_name = data.get('lastName')

    if not first_name or not last_name:
        response.status = 400
        return {"error": "First Name and Last Name are required"}

    user_id = request.user.get('user_id')
    user = db.app_user(user_id)
    if not user:
        response.status = 404
        return {"error": "User not found"}

    user.update_record(first_name=first_name, last_name=last_name)

    return {"message": "Profile updated successfully", "firstName": first_name, "lastName": last_name}


@action('user/password', method=['POST', 'OPTIONS'])
@enable_cors
@token_required
@action.uses(db)
def change_password():
    data = request.json
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')

    if not current_password or not new_password:
        response.status = 400
        return {"error": "Current and new password are required"}

    if len(new_password) < 6:
        response.status = 400
        return {"error": "New password must be at least 6 characters"}

    user_id = request.user.get('user_id')
    user = db.app_user(user_id)
    if not user:
        response.status = 404
        return {"error": "User not found"}

    if not bcrypt.checkpw(current_password.encode('utf-8'), user.password.encode('utf-8')):
        response.status = 401
        return {"error": "Incorrect current password"}

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    user.update_record(password=hashed_password)

    return {"message": "Password changed successfully"}


def bind_auth(safe_mount):
    """Bind auth routes to the app."""
    safe_mount('/user', 'GET', user)
    safe_mount('/user', 'OPTIONS', user)
    safe_mount('/user', 'PUT', update_profile)
    # OPTIONS for /user is already mounted via user(), but safe_mount handles duplicates gracefully

    safe_mount('/user/password', 'POST', change_password)
    safe_mount('/user/password', 'OPTIONS', change_password)

    safe_mount('/signup', 'POST', signup)
    safe_mount('/signup', 'OPTIONS', signup)

    safe_mount('/signin', 'POST', signin)
    safe_mount('/signin', 'OPTIONS', signin)
