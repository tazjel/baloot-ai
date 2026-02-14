import jwt
import time
import os
import logging
import server.settings as settings

logger = logging.getLogger(__name__)

# Use settings.SESSION_SECRET_KEY if available, otherwise fallback or env
_INSECURE_DEFAULTS = {'dev-secret-key-change-in-prod', 'secret', 'changeme', ''}

SECRET_KEY = settings.SESSION_SECRET_KEY or os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-prod')

# Warn on insecure defaults (but don't crash — allows dev mode)
if SECRET_KEY in _INSECURE_DEFAULTS or len(SECRET_KEY) < 16:
    logger.warning(
        "⚠️  JWT_SECRET is insecure or too short! "
        "Set a strong JWT_SECRET (32+ chars) in environment for production."
    )

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
