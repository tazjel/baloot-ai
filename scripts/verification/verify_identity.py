
import socketio
import time
import sys

def verify_identity():
    """
    Connects to the server, creates a room, and verifies that:
    1. Bots join automatically.
    2. Bots have correct Names (Saad, Khalid, Abu Fahad).
    3. Bots have correct Avatar IDs.
    """
    print("Verifying Unified Bot Identity...")
    
    sio = socketio.Client()
    results = {'players': []}
    
    @sio.event
    def connect():
        print("Connected to server.")

    @sio.event
    def player_joined(data):
        p = data['player']
        print(f"Player Joined: {p['name']} (Bot: {p.get('isBot')}) Avatar: {p.get('avatar')}")
        results['players'].append(p)
        
        # Once we have 4 players, check identities
        if len(results['players']) == 4:
            sio.disconnect()

    try:
        sio.connect('http://localhost:3005')
        
        # 1. Create Room
        room_id_container = {}
        def on_create(data):
            room_id_container['id'] = data['roomId']
            
        sio.emit('create_room', {}, callback=on_create)
        
        # Wait for callback
        start_wait = time.time()
        while 'id' not in room_id_container and time.time() - start_wait < 2:
            time.sleep(0.1)
            
        room_id = room_id_container.get('id')
        if not room_id:
            print("FAILED: Could not create room.")
            sys.exit(1)
            
        print(f"Room Created: {room_id}")

        # 2. Join Room as Human
        sio.emit('join_room', {'roomId': room_id, 'playerName': 'Verifier'})
        
        # Wait for players to join
        start_wait = time.time()
        while len(results['players']) < 4 and time.time() - start_wait < 5:
            time.sleep(0.1)
            
        if len(results['players']) < 4:
            print(f"FAILED: Timeout waiting for bots. Only found: {len(results['players'])}")
            sys.exit(1)
            
        # 3. Verify Identities
        bots = [p for p in results['players'] if p['isBot']]
        
        expected_names = ["Saad (Bot)", "Khalid (Bot)", "Abu Fahad (Bot)"]
        expected_avatars = ["avatar_saad", "avatar_khalid", "avatar_abu_fahad"]
        
        found_names = [b['name'] for b in bots]
        found_avatars = [b['avatar'] for b in bots]
        
        print("\n--- Verification Results ---")
        
        # Check Names
        for name in expected_names:
            if name in found_names:
                print(f"✅ Found Bot: {name}")
            else:
                print(f"❌ MISSING Bot: {name}")
                
        # Check Avatars
        for av in expected_avatars:
            if av in found_avatars:
                print(f"✅ Found Avatar: {av}")
            else:
                print(f"❌ MISSING Avatar: {av}")
                
        if all(n in found_names for n in expected_names) and all(a in found_avatars for a in expected_avatars):
            print("\nSUCCESS: All identities verified!")
        else:
            print("\nFAILURE: Identity mismatch.")
            sys.exit(1)

    except Exception as e:
        print(f"Verification Error: {e}")
        sys.exit(1)
    finally:
        if sio.connected:
            sio.disconnect()

if __name__ == "__main__":
    verify_identity()
