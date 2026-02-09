"""
Authentication routes: signup, signin, user profile, token_required decorator.
"""
import bcrypt
from py4web import action, request, response, abort
from server.common import db
import server.auth_utils as auth_utils


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

    print(f"{email} is signing up!")

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
    data = request.json
    email = data.get('email')
    password = data.get('password')

    print("User is signing in!")

    if not email or not password:
        return {"error": "Email and password are required"}

    user = db(db.app_user.email == email).select().first()

    if not user:
        print("user not found!")
        response.status = 404
        return {"error": "User not found"}

    if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        token = auth_utils.generate_token(user.id, user.email, user.first_name, user.last_name)
        response.status = 200
        return {"email": user.email, "firstName": user.first_name, "lastName": user.last_name, "token": token}

    return {"error": "Invalid credentials"}


def bind_auth(safe_mount):
    """Bind auth routes to the app."""
    safe_mount('/user', 'GET', user)
    safe_mount('/signup', 'POST', signup)
    safe_mount('/signup', 'OPTIONS', signup)
    safe_mount('/signin', 'POST', signin)
