"""
Client telemetry log handler.
"""
import time


def register(sio):
    """Register telemetry event handlers on the given sio instance."""

    @sio.event
    def client_log(sid, data):
        """Receive telemetry logs from client"""
        try:
            category = data.get('category', 'CLIENT')
            level = data.get('level', 'INFO')
            msg = data.get('message', '')

            log_line = f"[{level}] [{category}] {msg}"
            print(f"[CLIENT-LOG] [SID:{sid}] {log_line}")

            # Write to file for Agent to read
            with open('logs/client_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {log_line}\n")

        except Exception as e:
            print(f"Error logging client message: {e}")
