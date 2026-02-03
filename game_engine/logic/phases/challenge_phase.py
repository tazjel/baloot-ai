import logging
import enum

logger = logging.getLogger(__name__)

class GamePhase(enum.Enum):
    WAITING = 'WAITING'
    BIDDING = 'BIDDING'
    PLAYING = 'PLAYING'
    CHALLENGE = 'CHALLENGE'
    GAMEOVER = 'GAMEOVER'

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
        
        logger.info(f"[QAYD] Player {player_index} triggering Qayd investigation (via ChallengePhase)")
        
        # Delegate to TrickManager (Logic remains there for now)
        result = self.game.trick_manager.propose_qayd(player_index)
        
        if result.get('success'):
            # 1. Lock Game
            self.game.is_locked = True
            
            # 2. Change Phase
            self.game.phase = GamePhase.CHALLENGE.value
            
            # 3. Initialize State
            if not self.game.qayd_state:
                self.game.qayd_state = {'active': True, 'reporter': player_index}
            self.game.qayd_state['active'] = True
            
            logger.info(f"[QAYD] Challenge Handler: Game LOCKED & Phase set to CHALLENGE")
            return result
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
