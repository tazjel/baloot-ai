import logging
import json
import time
import os

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "server_manual.log")


# ═══════════════════════════════════════════════════════════════════
#  Structured Formatter
#  Output: [TIMESTAMP] [LEVEL] [MODULE] [ROOM_ID] Message | key=value
# ═══════════════════════════════════════════════════════════════════

class StructuredFormatter(logging.Formatter):
    """Produces structured log lines with optional key=value context."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname
        module = record.name

        # Pull room_id from the record if injected by GameLoggerAdapter
        room_id = getattr(record, 'room_id', '-')

        message = record.getMessage()

        # Build extras from adapter context (skip standard fields)
        extras = getattr(record, '_extras', {})
        extra_str = ""
        if extras:
            pairs = [f"{k}={v}" for k, v in extras.items() if k != 'room_id']
            if pairs:
                extra_str = " | " + " ".join(pairs)

        return f"[{timestamp}] [{level}] [{module}] [{room_id}] {message}{extra_str}"


class GameLoggerAdapter(logging.LoggerAdapter):
    """
    Adapter that injects room_id and optional context into log records.

    Usage:
        base_logger = logging.getLogger("GameServer")
        logger = GameLoggerAdapter(base_logger, room_id="abc123")
        logger.info("Player joined", player="Abu Fahad")
    """

    def __init__(self, logger: logging.Logger, room_id: str = "-", **kwargs):
        extra = {"room_id": room_id, **kwargs}
        super().__init__(logger, extra)

    def process(self, msg, kwargs):
        # Merge adapter extras into record
        extras = dict(self.extra)

        # Allow per-call overrides: logger.info("msg", extra={"player": "X"})
        call_extra = kwargs.get('extra', {})
        extras.update(call_extra)

        room_id = extras.pop('room_id', '-')

        kwargs['extra'] = {
            'room_id': room_id,
            '_extras': extras,
        }
        return msg, kwargs


# ═══════════════════════════════════════════════════════════════════
#  Logger Setup
# ═══════════════════════════════════════════════════════════════════

structured_formatter = StructuredFormatter()

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(structured_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(structured_formatter)

logger = logging.getLogger("GameServer")
logger.setLevel(logging.INFO)
logger.propagate = False

# Prevent duplicate handlers on reload
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# ═══════════════════════════════════════════════════════════════════
#  Structured Event Logging  (backward-compatible)
# ═══════════════════════════════════════════════════════════════════

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

    logger.info(f"[EVENT] {json.dumps(payload)}")

def log_error(game_id: str, error_msg: str, context: dict = None):
    logger.error(f"[ERROR] Game: {game_id} | Msg: {error_msg} | Context: {context}")
