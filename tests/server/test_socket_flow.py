import socketio
import time
import pytest

def test_dealer_randomness_via_socket():
    """
    Connects to the running game server 20 times.
    Creates a room, joins, and checks the dealer index in the 'game_start' event.
    """
    
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    
    for i in range(20):
        sio = socketio.Client()
        results = {}

        @sio.event
        def connect():
            print("Connected")

        @sio.event
        def game_start(data):
            dealer = data['gameState']['dealerIndex']
            results['dealer'] = dealer
            sio.disconnect()

        try:
            sio.connect('http://localhost:3005')
            
            # 1. Create Room
            # We need to simulate the events. 
            # Looking at socket_handler.py:
            # create_room(sid, data) -> returns roomId
            # But standard checks are usually callbacks.
            
            # Simple flow: 
            # Client emits 'create_room', gets callback with roomId.
            # Client emits 'join_room'.
            
            room_id_container = {}
            
            def on_create(data):
                room_id_container['id'] = data['roomId']
                
            sio.emit('create_room', {}, callback=on_create)
            
            # Wait for callback
            start_wait = time.time()
            while 'id' not in room_id_container and time.time() - start_wait < 2:
                time.sleep(0.1)
                
            room_id = room_id_container.get('id')
            assert room_id is not None
            
            # 2. Join Room (Triggers Bot Auto-Join and Game Start)
            sio.emit('join_room', {'roomId': room_id, 'playerName': 'TestUser'})
            
            # Wait for game_start event
            start_wait = time.time()
            while 'dealer' not in results and time.time() - start_wait < 2:
                time.sleep(0.1)
                
            if 'dealer' in results:
                counts[results['dealer']] += 1
                print(f"Run {i}: Dealer is {results['dealer']}")
            else:
                print(f"Run {i}: Timeout waiting for game start")
                
        except Exception as e:
            print(f"Run {i} failed: {e}")
        finally:
            if sio.connected:
                sio.disconnect()
                
    print("Final Counts:", counts)
    # Check if we have variance. If counts[0] == 20, BUG CONFIRMED.
    unique_dealers = [k for k, v in counts.items() if v > 0]
    assert len(unique_dealers) > 1, f"Dealer is not random! Counts: {counts}"

if __name__ == "__main__":
    test_dealer_randomness_via_socket()
