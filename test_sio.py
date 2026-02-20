"""
Quick Socket.IO diagnostic — tests queue_join callback against the server.

Usage:
    python test_sio.py                           # Cloud Run
    python test_sio.py http://localhost:3005      # Local
"""
import sys
import socketio

SERVER_URL = sys.argv[1] if len(sys.argv) > 1 else (
    "https://baloot-server-1076165534376.me-central1.run.app"
)

sio = socketio.Client(logger=True, engineio_logger=True)


@sio.event
def connect():
    print("\n✅ Connected!")
    print("Emitting queue_join...")
    sio.emit(
        'queue_join',
        {'playerName': 'test_user_1'},
        callback=on_response,
    )


def on_response(response):
    print(f"\n✅ Response received: {response}")
    sio.disconnect()


@sio.event
def disconnect():
    print("Disconnected!")


if __name__ == '__main__':
    print(f"Connecting to {SERVER_URL} ...")
    # Use polling first — more reliable with Cloud Run proxy
    sio.connect(SERVER_URL, transports=['polling', 'websocket'])
    sio.wait()
