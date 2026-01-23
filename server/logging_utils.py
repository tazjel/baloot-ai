import logging
import json
import time
import os

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "server_manual.log")

# Configure standard logger
# We use a FileHandler to ensure logs persist even if stdout is captured/redirected elsewhere
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger("GameServer")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_event(event_type: str, game_id: str = "GLOBAL", player_index: int = -1, details: dict = None):
    """
    Log a structured event for game analysis.
    Output: JSON string tagged with [EVENT].
    """
    if details is None: details = {}
    
    payload = {
        "event": event_type,
        "game_id": game_id,
        "timestamp": time.time(),
        "details": details
    }
    
    if player_index >= 0:
        payload["player_index"] = player_index

    # Use a specific marker for easy parsing
    logger.info(f"[EVENT] {json.dumps(payload)}")

def log_error(game_id: str, error_msg: str, context: dict = None):
    logger.error(f"[ERROR] Game: {game_id} | Msg: {error_msg} | Context: {context}")
