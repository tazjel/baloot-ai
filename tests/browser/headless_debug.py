
import socketio
import time
import sys

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BLUE = '\033[94m'

sio = socketio.Client()
room_id = None
my_player_index = -1

@sio.event
def connect():
    print(f"{GREEN}Connected to Game Server!{RESET}")

@sio.event
def connect_error(data):
    print(f"{RED}Connection Failed:{RESET}", data)

@sio.event
def disconnect():
    print(f"{RED}Disconnected.{RESET}")

@sio.event
def disconnect():
    print(f"{RED}Disconnected.{RESET}")

def create_room_callback(data):
    global room_id
    room_id = data['roomId']
    print(f"{BLUE}Room Created via Callback: {room_id}{RESET}")
    
    # Add Bots
    print("Adding Bot 1...")
    sio.emit('add_bot', {'roomId': room_id})

@sio.on('player_joined')
def on_player_joined(data):
    player = data['player']
    print(f"Player Joined: {player['name']} (Index: {player.get('index')})")
    
    # We don't have direct player count here easily unless we track it
    # But for headless debug, we can just sequentially add bots based on logic
    # Or just spam add_bot 3 times after creation
    
    # Logic: If I just joined, add Bot 1. If Bot 1 joined, add Bot 2...
    # But `add_bot` relies on server handling the count.
    
    # Better approach for CLI:
    # Just emit add_bot 3 times with small delay in main loop/callback
    pass

@sio.on('game_start')
def on_game_start(data):
    print(f"{GREEN}>>> GAME STARTED! <<<{RESET}")
    # Initialize basic state tracking if needed

@sio.on('game_state_update')
def on_game_state(data):
    phase = data.get('phase', 'UNKNOWN')
    turn_idx = data.get('currentTurnIndex', -1)
    
    # Pretty print state
    print(f"\n{YELLOW}--- STATE UPDATE ({phase}) ---{RESET}")
    print(f"Turn: Player {turn_idx}")
    
    if phase == 'BIDDING':
        print(f"Bidding Round: {data.get('biddingRound')}, Floor: {data.get('floorCard')}")
    elif phase == 'PLAYING':
        print(f"Table Cards: {len(data.get('tableCards', []))}")
        
    # Check if game is "Frozen" (Bot loop hanging?)
    # If the turn stays on a BOT for too long, we know it's stuck.

@sio.on('error')
def on_error(data):
    print(f"{RED}ERROR: {data}{RESET}")

def main():
    try:
        url = 'http://localhost:3001'
        print(f"Connecting to {url}...")
        sio.connect(url)
        
        # Create Room
        print("Creating Room...")
        sio.emit('create_room', {'player_name': 'HeadlessDebugger'}, callback=create_room_callback)
        
        # Wait for room creation before adding bots
        # The callback is async in threaded mode.
        # We can just wait a bit in loop
        time.sleep(1)
        if room_id:
             print("Adding remaining bots...")
             sio.emit('add_bot', {'roomId': room_id})
             time.sleep(0.5)
             sio.emit('add_bot', {'roomId': room_id})
             time.sleep(0.5)
             sio.emit('add_bot', {'roomId': room_id})
        
        # Keep alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Stopping...")
        sio.disconnect()
    except Exception as e:
        print(f"{RED}Exception: {e}{RESET}")

if __name__ == '__main__':
    main()
