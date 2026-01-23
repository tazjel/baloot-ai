import socketio
import time
import sys
import json
import logging
import random

# Configure Logging for the Verifier itself
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [VERIFIER] - %(message)s')
logger = logging.getLogger("Verifier")

SERVER_URL = "http://localhost:3005"

clients = []
client_states = {} # map client_index -> last_state
game_id = None
is_running = True

def create_client(index, name):
    sio = socketio.Client()
    
    @sio.event
    def connect():
        logger.info(f"Client {index} ({name}) connected")
        
    @sio.event
    def disconnect():
        logger.info(f"Client {index} disconnected")

    @sio.event
    def game_update(data):
        # Update local state tracking
        client_states[index] = data['gameState']
        
    return sio

def get_valid_action(state, player_index):
    """
    Very dumb random AI.
    """
    phase = state.get('phase')
    turn_idx = state.get('currentTurnIndex')
    
    if turn_idx != player_index:
        return None
        
    if phase == 'BIDDING':
        # Randomly bid to ensure game starts
        if random.random() < 0.3: # 30% chance to bid
             valid_bids = ['SUN', 'HOKUM']
             action = random.choice(valid_bids)
             return {'action': 'BID', 'payload': {'action': action, 'suit': 'S'}} # Suit irrelevant for SUN/HOKUM usually, but passing S just in case
             
        return {'action': 'BID', 'payload': {'action': 'PASS'}}
        
    elif phase == 'PLAYING':
        my_hand = []
        players = state.get('players', [])
        if len(players) > player_index:
             my_hand = players[player_index].get('hand', [])
             
        if not my_hand:
            return None

        # --- Follow Suit Logic ---
        table_cards = state.get('tableCards', [])
        valid_cards = []
        
        if not table_cards:
            # First to play: Any card is valid
            valid_cards = my_hand
        else:
            # Must follow suit of the first card
            lead_suit = table_cards[0]['card']['suit']
            # Check if we have that suit
            formatted_hand = []
            same_suit_cards = []
            
            for c in my_hand:
                if c['suit'] == lead_suit:
                    same_suit_cards.append(c)
            
            if same_suit_cards:
                valid_cards = same_suit_cards
            else:
                # Can play anything (usually)
                valid_cards = my_hand
                
        if not valid_cards:
             valid_cards = my_hand # Fallback
            
        card = random.choice(valid_cards)
        return {'action': 'PLAY_CARD', 'payload': card}
        
    return None

def run_simulation():
    global game_id
    logger.info("--- Starting Full Game Simulation ---")
    
    # 1. Setup Clients
    names = ["Sim_Bot_1", "Sim_Bot_2", "Sim_Bot_3", "Sim_Bot_4"]
    main_sio = create_client(0, names[0])
    main_sio.connect(SERVER_URL)
    clients.append(main_sio)
    
    # 2. Create Room
    logger.info("Creating Room...")
    room_data = main_sio.call('create_room', {})
    game_id = room_data['roomId']
    logger.info(f"Room Created: {game_id}")
    
    # Join P1 (Main)
    main_sio.emit('join_room', {'roomId': game_id, 'playerName': names[0]})
    
    # Join others
    for i in range(1, 4):
        c = create_client(i, names[i])
        c.connect(SERVER_URL)
        c.emit('join_room', {'roomId': game_id, 'playerName': names[i]})
        clients.append(c)
        time.sleep(0.2) # clear registration
        
    logger.info("All players joined.")
    
    # 3. Game Loop
    sim_start = time.time()
    turns_played = 0
    
    while is_running and (time.time() - sim_start < 60): # 60s max timeout
        # Check states
        active_state = None
        for i, s in client_states.items():
            if s: active_state = s; break
            
        if not active_state:
            time.sleep(0.5)
            continue
            
        # Check Game Over
        if active_state.get('phase') == 'FINISHED':
            logger.info(f"Game Finished! Winner: {active_state.get('winner')}")
            break
            
        # Check whose turn it is
        current_turn = active_state.get('currentTurnIndex')
        phase = active_state.get('phase')
        
        if current_turn is not None and 0 <= current_turn < 4:
            client = clients[current_turn]
            action = get_valid_action(active_state, current_turn)
            
            if action:
                logger.info(f"Player {current_turn} doing {action['action']} in {phase}")
                client.emit('game_action', {
                    'roomId': game_id, 
                    'action': action['action'], 
                    'payload': action['payload']
                })
                turns_played += 1
                time.sleep(0.1) # Debounce
            else:
                # Maybe waiting or animating
                pass
        
        time.sleep(0.2)
        
    logger.info(f"Simulation ended. Turns played: {turns_played}")
    
    for c in clients:
        c.disconnect()

if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Sim Failed: {e}")
