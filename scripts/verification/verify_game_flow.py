"""
E2E Game Flow Verifier — Connects 4 socket.io clients to the server,
creates a room, and plays a full game with random-but-legal moves.

Fixed issues from original:
  - Uses 'PLAY' action (not 'PLAY_CARD') to match server handler
  - Sends cardIndex (not raw card dict) in payload
  - Each client only acts when it's their turn
  - Tracks bidding rounds correctly (handles all-pass → re-deal)
  - Handles FINISHED → auto-restart gracefully
"""
import socketio
import time
import sys
import json
import logging
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [VERIFIER] - %(message)s')
logger = logging.getLogger("Verifier")

SERVER_URL = "http://localhost:3005"

# ──────────────────────────────────
# Shared State
# ──────────────────────────────────
clients = []
client_states = {}  # client_index → last game_state
game_id = None
is_running = True

# Counters
turns_played = 0
rounds_completed = 0
MAX_TURNS = 500
MAX_TIME = 120  # seconds


def create_client(index, name):
    sio = socketio.Client(reconnection=False, logger=False)

    @sio.event
    def connect():
        logger.info(f"Client {index} ({name}) connected")

    @sio.event
    def disconnect():
        logger.info(f"Client {index} disconnected")

    @sio.event
    def game_update(data):
        gs = data.get('gameState', data)
        client_states[index] = gs
        phase = gs.get('phase')
        turn = gs.get('currentTurnIndex')
        
        # Track round transitions
        global rounds_completed
        if phase == 'FINISHED':
            rounds_completed += 1
            logger.info(f"Round {rounds_completed} completed. Scores: "
                        f"Us={gs.get('matchScores', {}).get('us', '?')}, "
                        f"Them={gs.get('matchScores', {}).get('them', '?')}")

    @sio.event
    def game_start(data):
        gs = data.get('gameState', data)
        client_states[index] = gs
        logger.info(f"Client {index} received game_start")

    return sio


def get_valid_action(state, player_index):
    """
    Determine what action this player should take given the current game state.
    Returns None if it's not this player's turn or no action needed.
    """
    phase = state.get('phase')
    turn_idx = state.get('currentTurnIndex')

    # Only act if it's our turn
    if turn_idx != player_index:
        return None

    if phase == 'BIDDING':
        bid_state = state.get('bid', {})
        existing_type = bid_state.get('type')

        # If someone already bid, just pass
        if existing_type:
            return {'action': 'BID', 'payload': {'action': 'PASS'}}

        # 30% chance to bid SUN/HOKUM, otherwise pass
        if random.random() < 0.3:
            bid_type = random.choice(['SUN', 'HOKUM'])
            return {'action': 'BID', 'payload': {'action': bid_type}}

        return {'action': 'BID', 'payload': {'action': 'PASS'}}

    elif phase == 'PLAYING':
        players = state.get('players', [])
        if len(players) <= player_index:
            return None

        my_hand = players[player_index].get('hand', [])
        if not my_hand:
            return None

        table_cards = state.get('tableCards', [])
        valid_indices = []

        if not table_cards:
            # Leading: any card is valid
            valid_indices = list(range(len(my_hand)))
        else:
            # Must follow suit
            lead_suit = table_cards[0].get('card', {}).get('suit')
            same_suit = [i for i, c in enumerate(my_hand) if c.get('suit') == lead_suit]
            valid_indices = same_suit if same_suit else list(range(len(my_hand)))

        if not valid_indices:
            valid_indices = list(range(len(my_hand)))

        card_idx = random.choice(valid_indices)
        card = my_hand[card_idx]
        return {
            'action': 'PLAY',
            'payload': {
                'cardIndex': card_idx,
                'cardId': f"{card.get('rank', '?')}{card.get('suit', '?')}"
            }
        }

    return None


def run_simulation():
    global game_id, turns_played, is_running
    logger.info("=== Starting Full E2E Game Simulation ===")

    # 1. Setup Clients
    names = ["Sim_Bot_0", "Sim_Bot_1", "Sim_Bot_2", "Sim_Bot_3"]

    try:
        main_sio = create_client(0, names[0])
        main_sio.connect(SERVER_URL)
        clients.append(main_sio)
    except Exception as e:
        logger.error(f"Could not connect to server at {SERVER_URL}: {e}")
        sys.exit(1)

    # 2. Create Room
    logger.info("Creating room...")
    try:
        room_data = main_sio.call('create_room', {})
        game_id = room_data['roomId']
        logger.info(f"Room created: {game_id}")
    except Exception as e:
        logger.error(f"Failed to create room: {e}")
        sys.exit(1)

    # Join P0
    main_sio.emit('join_room', {'roomId': game_id, 'playerName': names[0]})
    time.sleep(0.3)

    # Join P1-P3
    for i in range(1, 4):
        c = create_client(i, names[i])
        c.connect(SERVER_URL)
        c.emit('join_room', {'roomId': game_id, 'playerName': names[i]})
        clients.append(c)
        time.sleep(0.3)

    logger.info("All 4 players joined.")
    time.sleep(0.5)

    # 3. Game Loop
    sim_start = time.time()
    stall_counter = 0
    last_turn_state = None

    while is_running and (time.time() - sim_start < MAX_TIME) and turns_played < MAX_TURNS:
        # Get the freshest state from any client
        active_state = None
        for i in range(4):
            s = client_states.get(i)
            if s:
                active_state = s
                break

        if not active_state:
            time.sleep(0.3)
            continue

        phase = active_state.get('phase')

        # Game Over
        if phase == 'GAMEOVER':
            us = active_state.get('matchScores', {}).get('us', 0)
            them = active_state.get('matchScores', {}).get('them', 0)
            logger.info(f"=== GAME OVER! Us: {us}, Them: {them} ===")
            break

        # FINISHED → wait for auto-restart (server handles this)
        if phase == 'FINISHED':
            time.sleep(0.5)
            continue

        # WAITING → game not started yet
        if phase == 'WAITING':
            time.sleep(0.3)
            continue

        current_turn = active_state.get('currentTurnIndex')

        if current_turn is None or not (0 <= current_turn < 4):
            time.sleep(0.2)
            continue

        # Detect stalls (same turn/phase for too long)
        current_key = (phase, current_turn, turns_played)
        if current_key == last_turn_state:
            stall_counter += 1
            if stall_counter > 20:
                logger.error(f"STALL DETECTED: stuck on {phase} turn={current_turn} for {stall_counter} cycles")
                break
        else:
            stall_counter = 0
            last_turn_state = current_key

        # Get action for the current player
        action = get_valid_action(active_state, current_turn)

        if action:
            client = clients[current_turn]
            logger.info(f"P{current_turn} → {action['action']} in {phase}")
            client.emit('game_action', {
                'roomId': game_id,
                'action': action['action'],
                'payload': action['payload']
            })
            turns_played += 1
            time.sleep(0.15)  # Debounce
        else:
            time.sleep(0.2)

    # Summary
    elapsed = time.time() - sim_start
    logger.info(f"=== Simulation ended ===")
    logger.info(f"  Turns played: {turns_played}")
    logger.info(f"  Rounds completed: {rounds_completed}")
    logger.info(f"  Time elapsed: {elapsed:.1f}s")

    if turns_played >= MAX_TURNS:
        logger.warning(f"Hit max turn limit ({MAX_TURNS})")
    if elapsed >= MAX_TIME:
        logger.warning(f"Hit time limit ({MAX_TIME}s)")

    # Disconnect
    for c in clients:
        try:
            c.disconnect()
        except:
            pass


if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
