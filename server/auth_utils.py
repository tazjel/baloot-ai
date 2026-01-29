import jwt
import time
import os
import server.settings as settings

# Use settings.SESSION_SECRET_KEY if available, otherwise fallback or env
SECRET_KEY = settings.SESSION_SECRET_KEY or os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-prod')

def generate_token(user_id, email, first_name, last_name):
    """
    Generate a new JWT token for the user.
    """
    payload = {
        "user_id": user_id,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "exp": time.time() + (24 * 3600)  # 24 Hour Expiry
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    """
    Verify the JWT token and return the payload if valid.
    Returns None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Handle expiry
    except jwt.InvalidTokenError:
        return None
