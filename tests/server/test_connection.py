import socketio
import time

sio = socketio.Client()

@sio.event
def connect():
    print("Test Script: Connected to Server!")
    sio.emit('create_room', {}, callback=on_create_room)

def on_create_room(data):
    print(f"Test Script: Room Created! {data}")
    sio.disconnect()

try:
    sio.connect('http://localhost:3005')
    sio.wait()
except Exception as e:
    print(f"Test Script: Connection Failed: {e}")
