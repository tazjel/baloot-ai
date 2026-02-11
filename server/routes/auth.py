"""
Authentication routes: signup, signin, user profile, token_required decorator.
"""
import logging
from py4web import action, request, response, abort
from server.common import db, auth
import server.auth_utils as auth_utils

logger = logging.getLogger(__name__)


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


@action('user', method=['GET'])
@token_required
@action.uses(db)
def user():
    """Protected endpoint returning user profile with league tier."""
    response.status = 200
    user_id = request.user.get('user_id')
    user_record = db.auth_user(user_id)

    # Use extra fields which we defined in common.py
    points = user_record.league_points if user_record and 'league_points' in user_record else 1000

    tier = "Bronze"
    if points >= 2000: tier = "Grandmaster"
    elif points >= 1800: tier = "Diamond"
    elif points >= 1600: tier = "Platinum"
    elif points >= 1400: tier = "Gold"
    elif points >= 1200: tier = "Silver"

    return {"user": request.user, "leaguePoints": points, "tier": tier}


@action('signup', method=['POST', 'OPTIONS'])
@action.uses(db, auth)
def signup():
    data = request.json
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    password = data.get('password')
    email = data.get('email')

    logger.info(f"{email} is signing up!")

    result = db.auth_user.validate_and_insert(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password
    )

    if result.get('errors'):
        logger.warning(f"Signup failed: {result['errors']}")
        response.status = 409
        return {"error": str(result['errors'])}

    user_id = result.get('id')

    response.status = 201
    return {
        "message": "User registered successfully",
        "email": email, "firstName": first_name,
        "lastName": last_name, "user_id": user_id
    }


@action('signin', method=['POST'])
@action.uses(db, auth)
def signin():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    logger.info("User is signing in!")

    if not email or not password:
        return {"error": "Email and password are required"}

    user, error = auth.login(email, password)

    if not user:
        logger.warning(f"Sign-in failed for {email}: {error}")
        response.status = 401
        return {"error": "Invalid credentials"}

    token = auth_utils.generate_token(user.id, user.email, user.first_name, user.last_name)
    response.status = 200
    return {"email": user.email, "firstName": user.first_name, "lastName": user.last_name, "token": token}


def bind_auth(safe_mount):
    """Bind auth routes to the app."""
    safe_mount('/user', 'GET', user)
    safe_mount('/signup', 'POST', signup)
    safe_mount('/signup', 'OPTIONS', signup)
    safe_mount('/signin', 'POST', signin)
