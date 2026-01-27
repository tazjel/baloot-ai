import socketio
import time
import sys
import logging
import random

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [E2E] - %(message)s')
logger = logging.getLogger("E2E_Verifier")

SERVER_URL = "http://localhost:3005"
sio = socketio.Client()
game_state = {}
my_index = None

@sio.event
def connect():
    logger.info("Connected to server.")

@sio.event
def disconnect():
    logger.info("Disconnected from server.")

@sio.event
def game_start(data):
    global game_state, my_index
    logger.info("Game Started!")
    game_state = data['gameState']
    
@sio.event
def game_update(data):
    global game_state
    game_state = data['gameState']
    logger.info(f"Phase: {game_state['phase']} | Turn: {game_state['currentTurnIndex']}")

@sio.event
def bot_speak(data):
    logger.info(f"Bot Speech: {data.get('message')} (Mood: {data.get('mood')})")

def get_action(state, player_idx):
    phase = state.get('phase')
    if phase == 'BIDDING':
        return {'action': 'BID', 'payload': {'action': 'PASS'}}
    elif phase == 'PLAYING':
        hand = state['players'][player_idx]['hand']
        # Simple Logic: Follow Suit or Random
        table = state.get('tableCards', [])
        if table:
             lead_suit = table[0]['card']['suit']
             followers = [i for i, c in enumerate(hand) if c['suit'] == lead_suit]
             if followers:
                  return {'action': 'PLAY', 'payload': {'cardIndex': followers[0]}}
        
        # Fallback
        return {'action': 'PLAY', 'payload': {'cardIndex': 0}}
    return None

def run_test():
    global my_index, game_state
    
    try:
        sio.connect(SERVER_URL)
        
        # 1. Create Room
        room = sio.call('create_room', {})
        room_id = room['roomId']
        logger.info(f"Created Room: {room_id}")
        
        # 2. Join (Server should auto-spawn 3 bots)
        join_res = sio.call('join_room', {'roomId': room_id, 'playerName': 'HumanTester'})
        if not join_res['success']:
             logger.error("Failed to join!")
             return
             
        my_index = join_res['yourIndex']
        logger.info(f"Joined as Player {my_index}. Waiting for bots...")
        
        # 3. Game Loop
        start_time = time.time()
        moves_made = 0
        
        while time.time() - start_time < 30: # Run for 30s
             if not game_state: 
                  time.sleep(1)
                  continue
                  
             if game_state.get('phase') == 'FINISHED':
                  logger.info("Game Finished!")
                  break
                  
             current_turn = game_state.get('currentTurnIndex')
             
             if current_turn == my_index:
                  action = get_action(game_state, my_index)
                  if action:
                       logger.info(f"My Turn. Action: {action['action']}")
                       sio.emit('game_action', {
                           'roomId': room_id,
                           'action': action['action'],
                           'payload': action['payload']
                       })
                       moves_made += 1
                       time.sleep(1) # simulate thinking
             else:
                  # Bot turn - wait
                  pass
             
             time.sleep(0.5)
             
        logger.info(f"Test Complete. Moves made by me: {moves_made}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        sio.disconnect()

if __name__ == "__main__":
    run_test()
