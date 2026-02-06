import logging

logger = logging.getLogger(__name__)

from game_engine.models.constants import GamePhase


class ChallengePhase:
    """
    Handles the 'CHALLENGE' (Qayd/Forensic) phase.
    
    Now a thin redirect to QaydEngine.
    Kept for backward compatibility with phases map.
    """
    
    def __init__(self, game_instance):
        self.game = game_instance
        
    def trigger_investigation(self, player_index):
        """Redirect to QaydEngine.trigger()."""
        return self.game.qayd_engine.trigger(player_index)

    def resolve_verdict(self):
        """Redirect to QaydEngine.confirm()."""
        return self.game.qayd_engine.confirm()
