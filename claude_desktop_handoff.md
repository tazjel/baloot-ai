# Claude Desktop Handoff: Debugging Matchmaking Queue Socket.IO Connection

Hey Claude! We are currently working on Load Testing the Matchmaking Queue for the Baloot AI project, but we've hit a Socket.IO connection snag on the deployed backend.

## The Goal
M-MP10: Load Test Matchmaking Queue
- Simulate 20-50 concurrent WebSocket connections to the matchmaking queue using Locust.
- Measure queue join latency and match formation time.
- Verify Rate Limiting (> 5 queue joins/min rejected).

## Current Status & What I've Done
1. **The Backend is Deployed:** The server is running on Google Cloud Run at `https://baloot-server-1076165534376.me-central1.run.app`.
2. **The Test Script:** We have a Locust test script at `tests/load/locustfile.py`.
3. **The Problem:** The Locust script successfully connects to the server (we see "Connection successful!"), but it gets stuck waiting for callbacks. When the script emits the `queue_join` event, the server never responds.
4. **My Investigation:**
   - I added verbose logging to `locustfile.py` to confirm the connect loop.
   - I created a raw python script `test_sio.py` using `socketio.Client(logger=True, engineio_logger=True)`.
   - Running `test_sio.py` showed that the Engine.IO layer connects successfully (polling -> websocket upgrade works), and it prints `Namespace / is connected`.
   - However, when it emits `queue_join` with `{'player_id': 'test_user_1', 'elo': 1200}`, no callback is triggered. It just hangs.

## What is Left to Do (Your Mission)
Please investigate why the Cloud Run backend is not responding to the `queue_join` event.

**Possible Culprits to Look Into:**
1. **Server-Side Event Handling:** Is `matchmaking_handler.py` correctly receiving the event? (Check `server/handlers/matchmaking_handler.py` and `server/socket_handler.py`).
2. **Version Mismatch:** Is there a `python-socketio` / `flask-socketio` version mismatch between the client (`requirements.txt` / `pyproject.toml`) and what the deployed server is running?
3. **Cloud Run WebSocket Support:** Does Cloud Run need specific concurrency settings, session affinity, or port mappings for Socket.IO to maintain the state? We currently have it deployed as a standard Cloud Run service.
4. **CORS/Origins:** Are the CORS settings in `socket_handler.py` restricting the events?

**Next Steps for You:**
1. Review `tests/load/locustfile.py`.
2. Review the server-side Socket.IO setup (`server/socket_handler.py` and `server/handlers/matchmaking_handler.py`).
3. You can run `python test_sio.py` to see the live debug output of the failing connection.
4. Identify the root cause and apply the fix (either to the client script or the server code).
5. Once fixed, run the locust load test to complete the M-MP10 objective.
