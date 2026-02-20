"""
Diagnostic script for Socket.IO callback issues on Cloud Run.

Tests BOTH create_room (known working handler) AND queue_join (matchmaking handler)
to determine if the issue is:
  - Handler-specific: create_room works but queue_join doesn't → stale deployment
  - Systemic: both fail → protocol/proxy issue

Usage:
    python tests/load/diagnose_sio.py [server_url]
    Default URL: https://baloot-server-1076165534376.me-central1.run.app
"""
import sys
import time
import threading
import socketio

SERVER_URL = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "https://baloot-server-1076165534376.me-central1.run.app"
)

TIMEOUT = 10  # seconds to wait for each callback

results = {
    "connect": None,
    "create_room": None,
    "queue_join": None,
    "queue_status": None,
}
events = {name: threading.Event() for name in results}


def run_test():
    sio = socketio.Client(logger=True, engineio_logger=True)

    @sio.event
    def connect():
        results["connect"] = "OK"
        events["connect"].set()
        print("\n✅ CONNECTED — running diagnostic tests...\n")

        # Test 1: create_room (known working handler)
        print("--- Test 1: create_room ---")
        sio.emit("create_room", {}, callback=on_create_room)

    @sio.event
    def disconnect():
        print("\n🔌 Disconnected.\n")

    def on_create_room(response):
        results["create_room"] = response
        events["create_room"].set()
        print(f"  ✅ create_room callback: {response}\n")

        # Test 2: queue_join (matchmaking handler — may be missing)
        print("--- Test 2: queue_join ---")
        sio.emit(
            "queue_join",
            {"playerName": "DiagBot"},
            callback=on_queue_join,
        )

    def on_queue_join(response):
        results["queue_join"] = response
        events["queue_join"].set()
        print(f"  ✅ queue_join callback: {response}\n")

        # Test 3: queue_status
        print("--- Test 3: queue_status ---")
        sio.emit("queue_status", {}, callback=on_queue_status)

    def on_queue_status(response):
        results["queue_status"] = response
        events["queue_status"].set()
        print(f"  ✅ queue_status callback: {response}\n")
        sio.disconnect()

    # Connect — use polling first (more reliable with Cloud Run proxy)
    print(f"\n🔗 Connecting to {SERVER_URL} ...")
    try:
        sio.connect(SERVER_URL, transports=["polling", "websocket"])
    except Exception as e:
        print(f"\n❌ Connection FAILED: {e}")
        return

    # Wait for connect
    if not events["connect"].wait(TIMEOUT):
        print("❌ Connection timed out (no connect event)")
        sio.disconnect()
        return

    # Wait for create_room (first test)
    if not events["create_room"].wait(TIMEOUT):
        print("❌ create_room callback TIMED OUT — server may not support acks")
        # Still try queue_join
        print("--- Test 2: queue_join (direct) ---")
        sio.emit(
            "queue_join",
            {"playerName": "DiagBot"},
            callback=on_queue_join,
        )

    # Wait for queue_join
    if not events["queue_join"].wait(TIMEOUT):
        print("❌ queue_join callback TIMED OUT")

    # Wait for queue_status
    if not events["queue_status"].wait(TIMEOUT):
        print("❌ queue_status callback TIMED OUT")

    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    for name, result in results.items():
        status = "✅" if result is not None else "❌ TIMED OUT"
        print(f"  {name:20s} → {status}  {result or ''}")

    print("\n--- Interpretation ---")
    if results["create_room"] and not results["queue_join"]:
        print("🔴 create_room works but queue_join doesn't.")
        print("   → The deployed server is MISSING the matchmaking handler.")
        print("   → Solution: Redeploy the Cloud Run service with latest code.")
    elif not results["create_room"] and not results["queue_join"]:
        print("🔴 BOTH create_room AND queue_join failed.")
        print("   → Fundamental protocol/proxy issue (Cloud Run or server).")
        print("   → Check Cloud Run logs for errors.")
    elif results["create_room"] and results["queue_join"]:
        print("🟢 Both events work! The server is functioning correctly.")
        print("   → The issue may be Locust-specific or load-related.")
    print()

    try:
        sio.disconnect()
    except Exception:
        pass


if __name__ == "__main__":
    run_test()
