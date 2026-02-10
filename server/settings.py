"""
This is an optional file that defined app level settings such as:
- database settings
- session settings
- i18n settings
This file is provided as an example:
"""
import os
from py4web.core import required_folder
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.local'))

# db settings
APP_FOLDER = os.path.dirname(__file__)
APP_NAME = os.path.split(APP_FOLDER)[-1]
# DB_FOLDER:    Sets the place where migration files will be created
#               and is the store location for SQLite databases
DB_FOLDER = required_folder(APP_FOLDER, "databases")
DB_URI = "sqlite://storage.db"
DB_POOL_SIZE = 1
DB_MIGRATE = True
DB_FAKE_MIGRATE = False  # maybe?

# location where static files are stored:
STATIC_FOLDER = required_folder(APP_FOLDER, "static")

# location where to store uploaded files:
UPLOAD_FOLDER = required_folder(APP_FOLDER, "uploads")

# send verification email on registration
VERIFY_EMAIL = True

# account requires to be approved ?
REQUIRES_APPROVAL = False

# auto login after registration
# requires False VERIFY_EMAIL & REQUIRES_APPROVAL
LOGIN_AFTER_REGISTRATION = False

# ALLOWED_ACTIONS in API / default Forms:
# ["all"]
# ["login", "logout", "request_reset_password", "reset_password", \
#  "change_password", "change_email", "profile", "config", "register",
#  "verify_email", "unsubscribe"]
# Note: if you add "login", add also "logout"
ALLOWED_ACTIONS = ["all"]

# email settings
SMTP_SSL = False
SMTP_SERVER = None
SMTP_SENDER = "you@example.com"
SMTP_LOGIN = "username:password"
SMTP_TLS = False

# session settings
SESSION_TYPE = "cookies"
SESSION_SECRET_KEY = None   # or replace with your own secret
MEMCACHE_CLIENTS = ["127.0.0.1:11211"]
REDIS_SERVER = "localhost:6379"
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "false").lower() == "true"


# logger settings
LOGGERS = [
    "warning:stdout",
    "debug:logs/debug.log"
]  # syntax "severity:filename" filename can be stderr or stdout

# ── Bot Speed Configuration ──────────────────────────────────────
# Set BALOOT_BOT_SPEED=fast for quick testing, or 'normal' for gameplay.
_BOT_SPEED = os.environ.get('BALOOT_BOT_SPEED', 'normal').lower()
BOT_TURN_DELAY    = 0.5 if _BOT_SPEED == 'fast' else 1.5   # Delay between bot actions
QAYD_RESULT_DELAY = 1.0 if _BOT_SPEED == 'fast' else 3.0   # Qayd result display time
SAWA_DELAY        = 0.2 if _BOT_SPEED == 'fast' else 0.5   # Sawa response delay

# i18n settings
T_FOLDER = required_folder(APP_FOLDER, "translations")

# Celery settings
USE_CELERY = False
CELERY_BROKER = "redis://localhost:6379/0"

# try import private settings
try:
    from .settings_private import *
except (ImportError, ModuleNotFoundError):
    pass
