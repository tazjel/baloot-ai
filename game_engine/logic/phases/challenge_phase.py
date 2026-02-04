import logging
import enum

logger = logging.getLogger(__name__)

from game_engine.models.constants import GamePhase

class ChallengePhase:
    """
    Handles all logic related to the 'CHALLENGE' (Qayd/Forensic) phase.
    Decouples Qayd state management from the main Game class.
    """
    
    def __init__(self, game_instance):
        self.game = game_instance
        # We access game state directly for now, but in future should use specialized interfaces
        
    def trigger_investigation(self, player_index):
        """
        Transitions the game into Qayd investigation mode.
        Replaces Game.handle_qayd_trigger
        """
        if self.game.is_locked:
            logger.warning(f"Qayd trigger rejected - game already locked")
            return {'success': False, 'error': 'Game Locked'}
        
        # 1. Lock Game IMMEDIATELY to prevent race conditions (double triggering)
        self.game.is_locked = True
        
        try:
            # Delegate to TrickManager (Logic remains there for now)
            result = self.game.trick_manager.propose_qayd(player_index)
            
            if result.get('success'):
                logger.info(f"[QAYD] Player {player_index} triggering Qayd investigation (via ChallengePhase)")
                
                # 2. Change Phase
                self.game.phase = GamePhase.CHALLENGE.value
                
                logger.info(f"[QAYD] Challenge Handler: Game LOCKED & Phase set to CHALLENGE")
                
                # LATENCY FIX: If reporter is AI, force immediate timer expiry
                # This makes the "Checking..." modal disappear instantly instead of waiting 5s+
                reporter_pos = result.get('reporter')
                reporter = next((p for p in self.game.players if p.position == reporter_pos), None)
                if reporter and reporter.is_bot:  # FIXED: Use .is_bot
                     import time
                     # TimerManager uses duration, not expiry_time!
                     # FIX: Use game.reset_timer() to ensure game.timer_paused is set to False!
                     self.game.reset_timer(0.1) 
                     logger.info(f"[QAYD] AI Reporter ({reporter.name}) detected - Forcing IMMEDIATE timer (0.1s) & Unpausing.")

                return result
            else:
                # UNLOCK if failed
                self.game.is_locked = False
                logger.error(f"[QAYD] propose_qayd FAILED: {result}")
                return result
        except Exception as e:
            self.game.is_locked = False
            logger.error(f"[QAYD] Exception during trigger: {e}")
            return {'success': False, 'error': str(e)}
        else:
            logger.error(f"[QAYD] propose_qayd FAILED: {result}")
            return result

    def resolve_verdict(self):
        """
        Handles the confirmation/resolution of a Qayd.
        """
        logger.info(f"[QAYD] confirm_qayd via ChallengePhase...")
        result = self.game.trick_manager.confirm_qayd()
        
        if result.get('success') or result.get('error') == "No Qayd details to confirm":
            self.game.is_locked = False
            logger.info(f"[QAYD] Challenge Handler: Game UNLOCKED after resolution (Success: {result.get('success')})")
        
        # Extra Safety: If state is not active, unlock
        if not self.game.trick_manager.qayd_state.get('active'):
             self.game.is_locked = False
            
        return result
