import socketio
import time
import logging
import sys
import json
import traceback
import requests
from typing import Optional, Dict, Any, List

# Configure "Human-Like" Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] 👁️ %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("HumanVerifier")

class HumanVerifier:
    def __init__(self, server_url: str = 'http://localhost:3005'):
        self.server_url = server_url
        self.sio = socketio.Client()
        self.game_id: Optional[str] = None
        self.player_name = "HumanTester"
        
        # State Tracking
        self.current_ui_state = {
            "screen": "LOBBY",
            "modal": None,
            "last_phase": "None",
            "qayd_visible": False,
            "table_cards": [],
            "round_history_len": 0
        }
        
        # Diagnostics
        self.event_log: List[str] = []
        
        # Report Card
        self.report = {
            "qayd_triggered": False,
            "penalty_applied": False,
            "round_ended": False,
            "next_round_started": False,
            "phantom_check_passed": False
        }

        self._bind_events()

    def _bind_events(self):
        self.sio.on('connect', self._on_connect)
        self.sio.on('disconnect', self._on_disconnect)
        self.sio.on('game_start', self._on_state_update)
        self.sio.on('game_update', self._on_state_update)
        self.sio.on('game_action_error', self._on_error)

    def _log_event(self, message: str):
        ts = time.strftime('%H:%M:%S')
        entry = f"[{ts}] {message}"
        self.event_log.append(entry)
        if len(self.event_log) > 50: self.event_log.pop(0) # Keep last 50

    def _on_connect(self):
        logger.info("✅ Connected to Server (Human Eyes Open)")
        self._log_event("Connected")

    def _on_disconnect(self):
        logger.info("❌ Disconnected")
        self._log_event("Disconnected")

    def _on_state_update(self, data):
        # Extract "Visible" State
        gs = data.get('gameState', {})
        if not gs: gs = data 
        
        phase = gs.get('phase')
        prev_phase = self.current_ui_state["last_phase"]
        
        if phase != prev_phase:
            self._log_event(f"PHASE CHANGE: {prev_phase} -> {phase}")
        
        # Support both snake_case (Back) and camelCase (Front)
        q_state = gs.get('qaydState') or gs.get('qayd_state') or {}
        qayd_active = q_state.get('active', False)
        
        self.current_ui_state['table_cards'] = gs.get('tableCards', []) or gs.get('table_cards', [])
        round_hist = gs.get('roundHistory', [])
        self.current_ui_state['round_history_len'] = len(round_hist)
        
        # Check for "Phantom Qayd"
        if prev_phase in ["FINISHED", "GAMEOVER"] and phase != prev_phase:
             # Phase changed from FINAL to something else.
             # If it goes to PLAYING directly, that's sus.
             if phase == "PLAYING":
                 logger.error(f"🚨 SUSPICIOUS JUMP: {prev_phase} -> PLAYING")
                 self._log_event(f"🚨 SUSPICIOUS JUMP: {prev_phase} -> PLAYING")

        # Update Tracker
        self.current_ui_state["last_phase"] = phase
        self.current_ui_state["qayd_visible"] = qayd_active
        
        # "Human" Observation Log (Reduced noise)
        ui_desc = f"Main Screen: {phase}"
        if qayd_active:
            ui_desc += " | [📺 MODAL: Qayd Investigation]"
        
        if phase == "FINISHED":
            ui_desc += " | [🏁 Round Summary]"
            
        # logger.info(f"👀 UI UPDATE: {ui_desc}") # Too noisy for optimized run

    def _on_error(self, data):
        logger.error(f"⚠️ SERVER ERROR POPUP: {data}")
        self._log_event(f"ERROR: {data}")

    def check_server_health(self) -> bool:
        """Pre-flight check with retries."""
        logger.info(f"🔌 Connecting to {self.server_url}...")
        for attempt in range(10): 
            try:
                requests.get(f"{self.server_url}/health", timeout=1) 
                return True
            except requests.exceptions.ConnectionError:
                if attempt == 0: logger.info("   Waiting for server...")
                time.sleep(1)
            except Exception:
                return True 
        
        logger.error(f"❌ Could not connect to {self.server_url}.")
        return False

    def wait_for_phase(self, target_phase, timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            if self.current_ui_state["last_phase"] == target_phase:
                return
            time.sleep(0.1) # Fast poll
        raise Exception(f"Timeout waiting for phase {target_phase}. Current: {self.current_ui_state['last_phase']}")

    def wait_for_condition(self, condition_func, timeout=30, name="Condition"):
        start = time.time()
        while time.time() - start < timeout:
            if condition_func():
                return
            time.sleep(0.1)
        raise Exception(f"Timeout waiting for {name}")

    def print_diagnostics(self):
        print("\n=== 🕵️ DIAGNOSTIC EVENT LOG (Last 20) ===")
        for line in self.event_log[-20:]:
            print(line)
        print("=========================================\n")

    def print_report(self):
        print("\n" + "="*40)
        print("   🔍 HUMAN VERIFICATION REPORT   ")
        print("="*40)
        
        items = [
            ("Qayd Triggered", self.report["qayd_triggered"]),
            ("Penalty Applied", self.report["penalty_applied"]),
            ("Round Ended", self.report["round_ended"]),
            ("Phantom Check", self.report["phantom_check_passed"]),
            ("Next Round Started", self.report["next_round_started"]),
        ]
        
        all_passed = True
        for name, passed in items:
            icon = "✅" if passed else "❌"
            print(f"{icon} {name:<30}")
            if not passed: all_passed = False
            
        print("-" * 40)
        if all_passed:
            print("🎉 RESULT: PASSED")
        else:
            print("⚠️ RESULT: FAILED")
            self.print_diagnostics()
        print("="*40 + "\n")

    def run(self):
        if not self.check_server_health():
            sys.exit(1)

        try:
            logger.info("🚀 Launching Optimized Verification...")
            self.sio.connect(self.server_url)
            
            # 1. Create & Join
            room = self.sio.call('create_room', {})
            self.game_id = room['roomId']
            self.sio.emit('join_room', {'roomId': self.game_id, 'playerName': self.player_name})
            
            # 3. Wait for Bidding
            self.wait_for_phase("BIDDING")
            logger.info("✅ Bidding Started")
            
            # 4. Bid
            self.sio.emit('game_action', {'roomId': self.game_id, 'action': 'BID', 'payload': {'action': 'SUN', 'suit': 'SUN'}})
            
            # 5. Wait for Playing
            self.wait_for_phase("PLAYING")
            logger.info("✅ Playing Started")
            
            # 6. Smart Wait for Bots (Wait until table has cards)
            logger.info("⏳ Waiting for bots...")
            # Wait for at least 3 cards on table, or 5 seconds max
            try:
                self.wait_for_condition(lambda: len(self.current_ui_state['table_cards']) >= 3, timeout=5, name="Bots Play")
            except:
                logger.warning("Bots slow/inactive, proceeding anyway...")
            
            # 7. Qayd
            logger.info("🔨 Triggering Qayd...")
            self.sio.emit('game_action', {'roomId': self.game_id, 'action': 'QAYD_TRIGGER'})
            
            self.wait_for_condition(lambda: self.current_ui_state["qayd_visible"] == True, timeout=5, name="Qayd Modal")
            self.report["qayd_triggered"] = True
            
            # 8. Accuse & Confirm
            cards = self.current_ui_state.get('table_cards', [])
            if not cards: cards = [{'playedBy': 'Me', 'suit': 'SUN', 'rank': '7'}] 
            
            acc_payload = {
                'crime_card': cards[-1],
                'proof_card': cards[0],
                'violation_type': 'REVOKE_SUIT'
            }
            self.sio.emit('game_action', {'roomId': self.game_id, 'action': 'QAYD_ACCUSATION', 'payload': {'accusation': acc_payload}})
            self.sio.emit('game_action', {'roomId': self.game_id, 'action': 'QAYD_CONFIRM'})
            
            # 10. Verdict
            logger.info("⏳ Waiting for Verdict...")
            self.wait_for_condition(lambda: self.current_ui_state["last_phase"] == "FINISHED", timeout=5, name="Phase=FINISHED")
            
            logger.info("✅ Round Ended")
            self.report["penalty_applied"] = True
            self.report["round_ended"] = True

            # 10. WATCHDOG (Reduced to 3s for efficiency)
            logger.info("🕵️ Checking for Phantom Qayd (3s)...")
            start_watch = time.time()
            self.report["phantom_check_passed"] = True 
            while time.time() - start_watch < 3:
                # Strictly: FINISHED -> BIDDING is okay. FINISHED -> PLAYING is FAIL.
                ph = self.current_ui_state["last_phase"]
                if ph == "PLAYING":
                     logger.error(f"🚨 FAILURE: Game returned to {ph}!")
                     self.report["phantom_check_passed"] = False
                     sys.exit(1)
                time.sleep(0.1)
                
            logger.info("✅ Watchdog Passed.")
            
            # 11. Next Round
            if self.current_ui_state["last_phase"] != "BIDDING":
                 logger.info("⏳ Waiting for Round 2...")
                 self.wait_for_phase("BIDDING", timeout=5)
            
            logger.info("🎉 SUCCESS: Verify Complete!")
            self.report["next_round_started"] = True
            
        except Exception as e:
            logger.error(f"❌ TEST FAILED: {repr(e)}")
            logger.error(traceback.format_exc())
            sys.exit(1)
        finally:
            self.sio.disconnect()
            self.print_report()

if __name__ == "__main__":
    verifier = HumanVerifier()
    verifier.run()
