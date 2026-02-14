"""
Client telemetry log handler.
"""
import os
import time
import logging

logger = logging.getLogger(__name__)

# Ensure logs directory exists at import time
os.makedirs('logs', exist_ok=True)

# Limit log line length to prevent log injection / disk exhaustion
MAX_LOG_LINE_LEN = 2000


def register(sio):
    """Register telemetry event handlers on the given sio instance."""

    @sio.event
    def client_log(sid, data):
        """Receive telemetry logs from client"""
        if not isinstance(data, dict):
            return
        try:
            category = str(data.get('category', 'CLIENT'))[:32]
            level = str(data.get('level', 'INFO'))[:8]
            msg = str(data.get('message', ''))[:MAX_LOG_LINE_LEN]

            log_line = f"[{level}] [{category}] {msg}"
            logger.info(f"[CLIENT-LOG] [SID:{sid}] {log_line}")

            # Write to file for Agent to read
            with open('logs/client_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {log_line}\n")

        except Exception as e:
            logger.error(f"Error logging client message: {e}")
