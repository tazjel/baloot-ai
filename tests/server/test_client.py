import socketio
import time
import sys

# Create a Socket.IO client
sio = socketio.Client()

@sio.event
def connect():
    print("Test Client Connected!")

@sio.event
def disconnect():
    print("Test Client Disconnected!")

@sio.event
def game_update(data):
    # print("State Update:", data)
    gs = data
    if 'gameState' in data: gs = data['gameState']
    
    phase = gs.get('phase')
    turn_idx = gs.get('currentTurnIndex')
    players = gs.get('players', [])
    
    print(f"Phase: {phase}, Turn: {turn_idx}")
    
    # Find me
    my_idx = -1
    for i, p in enumerate(players):
        if p.get('socketId') == sio.get_sid():
            my_idx = i
            break
            
    if my_idx != -1 and turn_idx == my_idx:
        print(f"MY TURN! (Index {my_idx})")
        
        if phase == 'BIDDING':
            print("Action: PASS")
            sio.emit('game_action', {'roomId': room_id, 'action': 'BID', 'payload': 'PASS'})
            
        elif phase == 'PLAYING':
            hand = players[my_idx].get('hand', [])
            if not hand:
                print("Hand empty?!")
                return
            
            # Simple Strategy: Play first card
            print(f"Action: PLAY Card 0")
            sio.emit('game_action', {'roomId': room_id, 'action': 'PLAY', 'payload': {'cardIndex': 0}})

@sio.event
def system_message(data):
    print("System:", data)

if __name__ == '__main__':
    try:
        sio.connect('http://localhost:3001')
        
        # Create Room
        print("Creating Room...")
        room_id = None
        
        def on_create(data):
            global room_id
            if data['success']:
                room_id = data['roomId']
                print(f"Room Created: {room_id}")
            else:
                print("Create failed:", data)
                sys.exit(1)
                
        sio.emit('create_room', {}, callback=on_create)
        
        # Wait for callback
        time.sleep(1)
        if not room_id:
             print("Timout creating room")
             sys.exit(1)

        # Add Bots
        print("Adding Bots...")
        sio.emit('add_bot', {'roomId': room_id})
        time.sleep(0.5)
        sio.emit('add_bot', {'roomId': room_id})
        time.sleep(0.5)
        sio.emit('add_bot', {'roomId': room_id})
        
        # Loop forever
        sio.wait()
        
    except Exception as e:
        print("Error:", e)
