"""
Load test for matchmaking queue using Locust + socketio.

Usage:
    locust -f tests/load/locustfile.py --host https://baloot-server-1076165534376.me-central1.run.app

Or for local testing:
    locust -f tests/load/locustfile.py --host http://localhost:3005

Environment variables:
    BALOOT_SERVER_URL  — Override the server URL (default: localhost:3005)
"""
import os
import socketio
import time
import uuid
import logging
from locust import User, task, between, events

# Server URL — use env var, Locust --host flag, or default
SERVER_URL = os.environ.get(
    "BALOOT_SERVER_URL",
    "https://baloot-server-1076165534376.me-central1.run.app",
)

logger = logging.getLogger(__name__)


class MatchmakingUser(User):
    # wait_time defines how long each simulated user waits between executing tasks
    wait_time = between(2, 5)

    # Class-level counter for unique user IDs
    _user_counter = 0

    def on_start(self):
        """Called when a Locust user starts."""
        # Generate unique ID for this simulated user
        MatchmakingUser._user_counter += 1
        self.user_id = f"loadtest_{MatchmakingUser._user_counter}_{uuid.uuid4().hex[:6]}"
        self.player_name = f"Bot_{MatchmakingUser._user_counter}"

        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.connected = False
        self.in_queue = False

        # Define Event Handlers
        @self.sio.on('connect')
        def on_connect():
            self.connected = True
            logger.info(f"[{self.user_id}] Connected to server")

        @self.sio.on('disconnect')
        def on_disconnect():
            self.connected = False
            self.in_queue = False
            logger.info(f"[{self.user_id}] Disconnected")

        @self.sio.on('match_found')
        def on_match_found(data):
            logger.info(f"[{self.user_id}] Match found: room={data.get('roomId')}")
            self.environment.events.request.fire(
                request_type="Socket.IO",
                name="match_found",
                response_time=0,
                response_length=len(str(data)),
                exception=None,
            )
            # Reset queue state — matched!
            self.in_queue = False

        @self.sio.on('error')
        def on_error(data):
            logger.warning(f"[{self.user_id}] Error: {data}")
            self.environment.events.request.fire(
                request_type="Socket.IO",
                name="error",
                response_time=0,
                response_length=len(str(data)),
                exception=Exception(
                    data.get('message', 'Unknown Error') if isinstance(data, dict) else str(data)
                ),
            )

        # Connect to server
        host = self.host or SERVER_URL
        try:
            logger.info(f"[{self.user_id}] Connecting to {host} ...")
            start = time.time()
            # Use polling first — more reliable with Cloud Run proxy.
            # Socket.IO will auto-upgrade to WebSocket after handshake.
            self.sio.connect(host, transports=['polling', 'websocket'])
            latency = int((time.time() - start) * 1000)
            self.environment.events.request.fire(
                request_type="Socket.IO",
                name="connect",
                response_time=latency,
                response_length=0,
                exception=None,
            )
            logger.info(f"[{self.user_id}] Connection successful ({latency}ms)")
        except Exception as e:
            logger.error(f"[{self.user_id}] Connection failed: {e}")
            self.environment.events.request.fire(
                request_type="Socket.IO",
                name="connect",
                response_time=0,
                response_length=0,
                exception=e,
            )

    def on_stop(self):
        """Called when a Locust user stops."""
        if self.connected:
            try:
                # Leave queue before disconnecting
                if self.in_queue:
                    self.sio.emit('queue_leave', {})
                self.sio.disconnect()
            except Exception:
                pass

    @task(3)
    def join_queue(self):
        """Simulates joining the matchmaking queue."""
        if not self.connected:
            logger.warning(f"[{self.user_id}] join_queue called but not connected")
            return

        if self.in_queue:
            # Already in queue, check status instead
            self._check_queue_status()
            return

        start_time = time.time()

        def callback(response):
            latency = int((time.time() - start_time) * 1000)
            logger.info(f"[{self.user_id}] queue_join response ({latency}ms): {response}")

            if isinstance(response, dict) and response.get('success'):
                self.in_queue = True
                self.environment.events.request.fire(
                    request_type="Socket.IO",
                    name="queue_join",
                    response_time=latency,
                    response_length=len(str(response)),
                    exception=None,
                )
            else:
                error_msg = response.get('error', 'Join Failed') if isinstance(response, dict) else str(response)
                self.environment.events.request.fire(
                    request_type="Socket.IO",
                    name="queue_join",
                    response_time=latency,
                    response_length=len(str(response)),
                    exception=Exception(error_msg),
                )

        self.sio.emit(
            'queue_join',
            {'playerName': self.player_name},
            callback=callback,
        )

    @task(1)
    def check_queue_status(self):
        """Periodically check queue status."""
        if not self.connected:
            return
        self._check_queue_status()

    def _check_queue_status(self):
        """Internal: emit queue_status and track response."""
        start_time = time.time()

        def callback(response):
            latency = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="Socket.IO",
                name="queue_status",
                response_time=latency,
                response_length=len(str(response)),
                exception=None,
            )

        self.sio.emit('queue_status', {}, callback=callback)
