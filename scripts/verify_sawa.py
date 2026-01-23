import socketio
import time
import sys

# Configuration
SERVER_URL = "http://localhost:3000"
SIO = socketio.Client()

def verify_sawa():
    print("--- Starting Sawa Verification ---")
    
    try:
        SIO.connect(SERVER_URL)
        print("Connected to server.")
        
        # 1. Create Room
        room_data = SIO.call('create_room', {})
        room_id = room_data['roomId']
        print(f"Room Created: {room_id}")
        
        # 2. Join as Main Player (Bottom)
        SIO.emit('join_room', {'roomId': room_id, 'playerName': 'Tester'})
        time.sleep(1) # Wait for bots to join
        
        # 3. Start Game Logic
        # We need to simulate the game flow until it's our turn to play.
        # But wait! Sawa can only be called on YOUR turn.
        
        # Helper to track state
        game_state = {'phase': None, 'turn': None}
        
        @SIO.event
        def player_joined(data):
            print(f"Player Joined: {data['player']['name']}")

        @SIO.event
        def game_start(data):
            print("Game Started!")
            game_state['phase'] = data['gameState']['phase']
            game_state['turn'] = data['gameState']['currentTurnIndex']
            
        @SIO.event
        def game_update(data):
            gs = data['gameState']
            game_state['phase'] = gs['phase']
            game_state['turn'] = gs['currentTurnIndex']
            
            # Print Sawa State
            if gs.get('sawaState'):
                print(f"SAWA STATE: {gs['sawaState']['status']} (Active: {gs['sawaState']['active']})")
            
        # Wait for bots to join and game to start
        print("Waiting for players and game start...")
        for i in range(10):
            if game_state['phase']: break
            time.sleep(1)
            print(".", end="")
        print("")
        
        if not game_state['phase']:
             print("Timeout: Game did not start.")
             return
        
        # Phase 1: Bidding
        # Just PASS until Play phase
        idx = 0
        while game_state['phase'] == 'BIDDING':
             if game_state['phase'] != 'BIDDING': break   
             
             if game_state['turn'] == 0:
                 print(f"My Turn (Bidding). Action: PASS. Phase: {game_state['phase']}")
                 SIO.emit('game_action', {'roomId': room_id, 'action': 'BID', 'payload': {'action': 'PASS'}})
                 time.sleep(1) # Wait longer after action
             time.sleep(0.5)
             
        # Phase 2: Playing
        print(f"Entered Phase: {game_state['phase']}. Waiting for my turn...")
        while True:
            # Check turn, phase, and Table Cards (must be empty to claim Sawa)
            # We need to access table cards. Game update gives us this.
            # But game_state dict only had phase/turn.
            pass
            if game_state['phase'] != 'PLAYING': break
            
            if game_state['turn'] == 0:
                 # Check if table is empty (we need to track this separately)
                 # Hack: Just try to call it. If it fails, wait for next turn? 
                 # But if I don't play, the game stalls.
                 # So I should play a card if Sawa fails.
                 
                 print("Attempting to CLAIM SAWA...")
                 res = SIO.call('game_action', {'roomId': room_id, 'action': 'SAWA'})
                 print(f"Sawa Result: {res}")
                 
                 if res and res.get('success'):
                     print("Sawa Claimed Successfully!")
                     break # Exit loop and wait for results
                 else:
                     print(f"Sawa Failed: {res}. Playing card to pass turn.")
                     # Play index 0
                     SIO.emit('game_action', {'roomId': room_id, 'action': 'PLAY', 'payload': {'cardIndex': 0}})
                     time.sleep(2) # Wait for others to play
            
            time.sleep(0.5)
        
        # Check if Sawa is active
        # We need to listen to the update. 
        # But to be robust, let's just assume we need to refuse/accept as bots.
        # Bots SHOULD auto-respond if logic is implemented.
        # Let's see if the server responds with a failure or update.
        
        print("Checking if Bots responded...")
        
        # Wait up to 10 seconds for resolution
        for i in range(20):
             state = game_state.get('sawaState', {})
             status = state.get('status')
             print(f"Wait {i}: Sawa Status: {status}")
             
             if status in ['ACCEPTED', 'REFUSED']:
                  print(f"Sawa Resolved! Status: {status}")
                  if status == 'REFUSED':
                       if state.get('challenge_active'):
                            print("Challenge Mode Activated (Expected).")
                       else:
                            print("Refused but no challenge? (Unexpected)")
                  break
             
             time.sleep(0.5)
             
        time.sleep(1)
        print("Test Complete. Check server logs for SAWA state.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        SIO.disconnect()

if __name__ == "__main__":
    verify_sawa()
