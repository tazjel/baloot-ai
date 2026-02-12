"""
game_engine/logic/sawa_manager.py — Sawa (Grand Slam) Declaration Manager
===========================================================================

Extracted from project_manager.py for single-responsibility.

Sawa = Declaring you guarantee winning ALL remaining tricks.
"""

from game_engine.logic.rules.sawa import check_sawa_eligibility as _check_sawa
from game_engine.models.constants import GamePhase
from server.logging_utils import logger


class SawaManager:
    def __init__(self, game):
        self.game = game

    def _build_played_cards_set(self) -> set:
        """
        Builds a set of all cards played this round (completed tricks + current table).
        Delegates to akka_manager's implementation to avoid duplication.
        """
        return self.game.akka_manager._build_played_cards_set()

    def check_sawa_eligibility(self, player_index) -> bool:
        """Wrapper checking Sawa eligibility for a player."""
        player = self.game.players[player_index]
        if not player.hand:
            return False

        return _check_sawa(
            hand=player.hand,
            played_cards=self._build_played_cards_set(),
            trump_suit=self.game.trump_suit,
            game_mode=self.game.game_mode,
            phase=self.game.phase
        )

    def handle_sawa(self, player_index):
        """Process a Sawa declaration."""
        try:
             player = self.game.players[player_index]

             # Validation: Must be PLAYING phase & Player's Turn
             if self.game.phase != GamePhase.PLAYING.value or player_index != self.game.current_turn:
                  return {"success": False, "error": "Invalid Timing"}

             eligible = self.check_sawa_eligibility(player_index)

             if not eligible:
                  # PENALTY / REFEREE
                  logger.warning(f"INVALID SAWA CLAIM by {player.position}")
                  self.game.increment_blunder(player_index)
                  return {
                      "success": False,
                      "error": "REFEREE_FLAG",
                      "intervention": {
                          "type": "INVALID_SAWA",
                          "playerIndex": player_index,
                          "message": "Sawa Rejected! You do not guarantee all tricks."
                      }
                  }

             # Valid Sawa
             logger.info(f"SAWA DECLARED VALID by {player.position}")

             self.game.sawa_declaration = {
                 'player_index': player_index,
                 'active': True
             }

             return {"success": True, "sawa_active": True}

        except Exception as e:
             logger.error(f"Error in handle_sawa: {e}")
             return {"success": False, "error": str(e)}
