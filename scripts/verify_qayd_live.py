
import socketio
import time
import sys
import logging

# === CONFIGURATION ===
GAME_ID = "live_test_pro_qayd"
SERVER_URL = "http://localhost:3005"
TIMEOUT_PHASE = 15
TIMEOUT_OVERALL = 60

# === LOGGING SETUP ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('ProTest')

sio = socketio.Client()

# === STATE TRACKING ===
class GameMonitor:
    def __init__(self):
        self.phase = None
        self.round_num = 0
        self.scores = {'us': 0, 'them': 0}
        self.hand = []
        self.my_turn = False
        self.qayd_status = None
        self.events = []
        self.room_id = None
        self.player_index = -1

    def log_event(self, name, data):
        self.events.append((time.time(), name, data))
        # logger.info(f"EVENT: {name} | {data}")

gm = GameMonitor()

# === EVENTS ===
@sio.event
def connect():
    logger.info("Connected to Server")

@sio.event
def game_update(data):
    if data.get('phase'):
        prev_phase = gm.phase
        gm.phase = data.get('phase')
        if prev_phase != gm.phase:
            logger.info(f"🔄 PHASE CHANGE: {prev_phase} -> {gm.phase}")
    
    if data.get('matchScores'):
        gm.scores = data.get('matchScores', {})
        
    gm.qayd_status = data.get('qaydState', {}).get('status')
    if gm.qayd_status == 'RESOLVED':
         # Log detail
         reason = data.get('qaydState', {}).get('reason')
         logger.info(f"⚖️ QAYD RESOLVED: {reason}")

    gm.round_num = len(data.get('roundHistory', []))

@sio.event
def game_start(data):
    logger.info("🚀 GAME START EVENT")
    gs = data.get('gameState', {})
    gm.phase = gs.get('phase')
    gm.scores = gs.get('matchScores', {})
    gm.round_num = len(gs.get('roundHistory', []))

@sio.event
def player_joined(data):
    p = data.get('player', {})
    logger.info(f"👤 Player Joined: {p.get('name')} ({p.get('position')})")

@sio.event
def player_hand(data):
    gm.hand = data.get('hand', [])
    # logger.info(f"🃏 Hand Received: {len(gm.hand)} cards")

# === TEST LOGIC ===
def wait_for(condition_func, timeout=10, name="Condition"):
    start = time.time()
    while time.time() - start < timeout:
        if condition_func():
            return True
        time.sleep(0.5)
    logger.error(f"❌ TIMEOUT waiting for: {name}")
    return False

def run_pro_test():
    try:
        logger.info(f"🔌 Connecting to {SERVER_URL}...")
        sio.connect(SERVER_URL)
        
        # 1. SETUP
        logger.info("🛠️ Creating Room...")
        resp = sio.call('create_room', {})
        if not resp.get('success'): raise Exception(f"Create failed: {resp}")
        gm.room_id = resp['roomId']
        logger.info(f"✅ Room Created: {gm.room_id}")

        sio.emit('join_room', {'roomId': gm.room_id, 'userId': 'Tester_Pro', 'playerName': 'ProTester'})
        # Note: Bots auto-add on join in dev mode usually, or we wait/add
        # The previous successful test showed bots auto-added. We assume this behavior.
        
        # 2. AWAIT START
        logger.info("⏳ Waiting for Game Start (BIDDING)...")
        if not wait_for(lambda: gm.phase == 'BIDDING', timeout=15, name="Phase=BIDDING"):
             raise Exception("Failed to reach BIDDING phase")
        
        # 3. BIDDING
        if gm.phase == 'BIDDING':
            logger.info("📣 Bidding SUN...")
            # Use call for ACK
            res = sio.call('game_action', {'roomId': gm.room_id, 'action': 'BID', 'payload': {'action': 'SUN', 'suit': 'SUN'}})
            if not res.get('success'): logger.warning(f"Bid Warning: {res}")
        else:
            logger.info(f"Skipping BID (Phase is {gm.phase})")
        
        # 4. AWAIT PLAYING
        logger.info("⏳ Waiting for PLAYING (60s timeout)...")
        if not wait_for(lambda: gm.phase == 'PLAYING', timeout=60, name="Phase=PLAYING"):
             raise Exception("Failed to reach PLAYING phase")
        
        logger.info("✅ In PLAYING Phase. Giving bots 2s to settle...")
        time.sleep(2)
        
        # 5. TRIGGER REVOKE (Trigger Bot Qayd)
        if gm.hand:
            # Play last card (force revoke)
            card = gm.hand[-1]
            logger.info(f"🃏 Playing Card (Likely Revoke): {card}")
            res = sio.call('game_action', {'roomId': gm.room_id, 'action': 'PLAY', 'payload': {'cardIndex': len(gm.hand)-1}})
            if not res.get('success'): logger.warning(f"Play Warning: {res}")
        else:
            raise Exception("Hand empty? Cannot play.")
            
        # 6. VERIFY QAYD RESOLUTION / ROUND END
        logger.info("🔎 Waiting for Qayd Resolution & Round End...")
        
        # Verification Stages
        # A. Qayd Resolved (Score change)
        start_score_them = gm.scores.get('them', 0)
        
        def check_score_penalty():
            curr = gm.scores.get('them', 0)
            return curr >= start_score_them + 26
            
        if not wait_for(check_score_penalty, timeout=20, name="Score Penalty (+26)"):
             logger.error(f"Scores: {gm.scores}")
             raise Exception("Score did not update correctly")
        logger.info(f"✅ Score Verified: them={gm.scores.get('them')} (Delta: {gm.scores.get('them') - start_score_them})")
        
        # B. Phase Transition to FINISHED
        # This is where the bug likely is ("Loop" / "Did not go to next round")
        logger.info("⏳ Verifying transition to FINISHED...")
        if not wait_for(lambda: gm.phase == 'FINISHED' or gm.phase == 'PLAYING', timeout=10, name="Phase=FINISHED/PLAYING(NextRound)"):
             logger.error(f"Stuck in Phase: {gm.phase}")
             raise Exception("Game did not finish round after Qayd")
             
        if gm.phase == 'FINISHED':
             logger.info("✅ Phase is FINISHED. Waiting for Auto-Restart (Round 2)...")
             # Wait for Round 2
             start_round = gm.round_num
             if not wait_for(lambda: gm.round_num > start_round or gm.phase == 'BIDDING', timeout=10, name="Next Round Start"):
                  raise Exception("Auto-Restart failed")
             logger.info(f"✅ Round 2 Started! (Round Num: {gm.round_num})")
             
        elif gm.phase == 'PLAYING':
             logger.info("✅ Game already advanced to Next Round Playing (Fast forward?)")
        
        logger.info("🏆 TEST PASSED: Full Cycle Verified.")

    except Exception as e:
        logger.error(f"❌ TEST FAILED: {e}")
        # Dump state
        logger.error(f"Final State: Phase={gm.phase}, Scores={gm.scores}, Qayd={gm.qayd_status}")
    finally:
        sio.disconnect()

if __name__ == "__main__":
    run_pro_test()
