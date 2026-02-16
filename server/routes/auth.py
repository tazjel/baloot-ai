"""
Authentication routes: signup, signin, user profile, token_required decorator.
"""
import bcrypt
import logging
from py4web import action, request, response, abort
from server.common import db
import server.auth_utils as auth_utils

logger = logging.getLogger(__name__)


def token_required(f):
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            abort(401, 'Authorization token is missing or invalid')

        try:
            token = auth_header.split(" ")[1]
        except IndexError:
            abort(401, 'Invalid Authorization header format')

        payload = auth_utils.verify_token(token)
        if not payload:
            abort(401, 'Invalid or Expired Token')

        request.user = payload
        return f(*args, **kwargs)

    return decorated


@action('user', method=['GET'])
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
def signup():
    data = request.json
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    password = data.get('password')
    email = data.get('email')

    if not email or not password or not first_name or not last_name:
        response.status = 400
        return {"error": "All fields are required"}

    if len(password) < 8:
        response.status = 400
        return {"error": "Password must be at least 8 characters"}

    logger.info(f"{email} is signing up!")

    existing_user = db(db.app_user.email == email).select().first()
    if existing_user:
        response.status = 409
        return {"error": "User already exists"}

    # Hash password and decode to string for consistent storage
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

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

    # Handle password stored as string (decoded) or possibly bytes (legacy)
    stored_password = user.password
    if isinstance(stored_password, str):
        stored_password = stored_password.encode('utf-8')

    if bcrypt.checkpw(password.encode('utf-8'), stored_password):
        token = auth_utils.generate_token(user.id, user.email, user.first_name, user.last_name)
        response.status = 200
        return {"email": user.email, "firstName": user.first_name, "lastName": user.last_name, "token": token}

    return {"error": "Invalid credentials"}


@action('user', method=['PUT'])
@token_required
@action.uses(db)
def update_profile():
    data = request.json
    first_name = data.get('firstName')
    last_name = data.get('lastName')

    # Validation
    if not first_name and not last_name:
         response.status = 400
         return {"error": "At least one field (firstName, lastName) is required"}

    update_data = {}
    if first_name: update_data['first_name'] = first_name
    if last_name: update_data['last_name'] = last_name

    user_id = request.user.get('user_id')
    db(db.app_user.id == user_id).update(**update_data)

    # Return updated user info
    user_record = db.app_user(user_id)
    return {
        "message": "Profile updated",
        "firstName": user_record.first_name,
        "lastName": user_record.last_name,
        "email": user_record.email
    }


@action('user/password', method=['POST'])
@token_required
@action.uses(db)
def change_password():
    data = request.json
    old_password = data.get('oldPassword')
    new_password = data.get('newPassword')

    if not old_password or not new_password:
        response.status = 400
        return {"error": "Both oldPassword and newPassword are required"}

    if len(new_password) < 8:
        response.status = 400
        return {"error": "New password must be at least 8 characters"}

    user_id = request.user.get('user_id')
    user_record = db.app_user(user_id)

    if not user_record:
        response.status = 404
        return {"error": "User not found"}

    # Verify old password
    stored_password = user_record.password
    if isinstance(stored_password, str):
        stored_password = stored_password.encode('utf-8')

    if not bcrypt.checkpw(old_password.encode('utf-8'), stored_password):
        response.status = 401
        return {"error": "Incorrect old password"}

    # Update with new password
    hashed_new = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_record.update_record(password=hashed_new)

    return {"message": "Password updated successfully"}


def bind_auth(safe_mount):
    """Bind auth routes to the app."""
    safe_mount('/user', 'GET', user)
    safe_mount('/signup', 'POST', signup)
    safe_mount('/signup', 'OPTIONS', signup)
    safe_mount('/signin', 'POST', signin)
    safe_mount('/user', 'PUT', update_profile)
    safe_mount('/user/password', 'POST', change_password)
