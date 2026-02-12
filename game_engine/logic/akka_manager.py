"""
game_engine/logic/akka_manager.py — Akka (Boss Card) Declaration Manager
=========================================================================

Extracted from project_manager.py for single-responsibility.

Akka = Declaring you hold the highest remaining non-trump card in a given
suit during HOKUM mode.

Rules (Standard Baloot):
  1. Mode: HOKUM only (no concept of Akka in SUN).
  2. Suit: Must be non-trump.
  3. Rank: Must NOT be Ace (self-evident boss).
  4. Condition: Must be the HIGHEST REMAINING card of that suit.
  5. Phase: Must be PLAYING phase.
  6. Turn: Must be the player's turn.
"""

import time
from typing import List, Optional

from game_engine.core.state import AkkaState
from game_engine.models.constants import GamePhase
from server.logging_utils import logger


class AkkaManager:
    def __init__(self, game):
        self.game = game

    def init_akka(self):
        """Reset Akka state for a new round."""
        self.game.state.akkaState = AkkaState()

    # ─── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _card_key(card) -> str:
        """
        Generates a consistent card signature string from any card format.
        Handles: Card objects, dicts, nested {card: ...} wrappers.
        Returns: e.g. "A♠", "10♥"
        """
        if isinstance(card, dict):
            if 'card' in card:
                return AkkaManager._card_key(card['card'])
            return f"{card.get('rank', '')}{card.get('suit', '')}"
        if hasattr(card, 'rank') and hasattr(card, 'suit'):
            return f"{card.rank}{card.suit}"
        return str(card)

    def _build_played_cards_set(self) -> set:
        """
        Builds a set of all cards played this round (completed tricks + current table).
        Uses _card_key for consistent format regardless of card representation.
        """
        played = set()

        # 1. Completed tricks from round_history
        for trick in self.game.round_history:
            for card_entry in trick.get('cards', []):
                key = self._card_key(card_entry)
                if key:
                    played.add(key)

        # 2. Cards currently on the table
        for tc in self.game.table_cards:
            key = self._card_key(tc.get('card', tc))
            if key:
                played.add(key)

        return played

    # ─── Eligibility ──────────────────────────────────────────────────

    def check_akka_eligibility(self, player_index) -> List[str]:
        """
        Returns a list of suits where the player holds the Boss card.
        Delegates to pure logic in rules/akka.py.
        """
        from game_engine.logic.rules.akka import check_akka_eligibility

        player = self.game.players[player_index]
        if not player.hand:
            return []

        return check_akka_eligibility(
            hand=player.hand,
            played_cards=self._build_played_cards_set(),
            trump_suit=self.game.trump_suit,
            game_mode=self.game.game_mode,
            phase=self.game.phase
        )

    # ─── Declaration ──────────────────────────────────────────────────

    def handle_akka(self, player_index):
        """
        Process an Akka declaration from a player.
        Validates eligibility, updates state, and returns result.
        """
        try:
            player = self.game.players[player_index]

            # --- Pre-validation guards (race condition defense) ---

            # Must be PLAYING phase
            if self.game.phase != GamePhase.PLAYING.value:
                return {
                    "success": False,
                    "error": f"Cannot declare Akka outside PLAYING phase (current: {self.game.phase})"
                }

            # Must be this player's turn
            if player_index != self.game.current_turn:
                return {
                    "success": False,
                    "error": "Not your turn to declare Akka"
                }

            # Must be HOKUM
            if self.game.game_mode != 'HOKUM':
                return {
                    "success": False,
                    "error": "Akka is only available in HOKUM mode"
                }

            # Validation: Already active
            if self.game.state.akkaState.active:
                 logger.warning(f"AKKA REJECTED: Already active (Claimer: {self.game.state.akkaState.claimer}). Request by: {player.position}")
                 return {'success': False, 'error': 'Already Active'}

            eligible = self.check_akka_eligibility(player_index)

            if not eligible:
                # INVALID AKKA — Referee Intervention
                logger.warning(f"INVALID AKKA CLAIM by {player.position}")
                self.game.increment_blunder(player_index)

                return {
                    "success": False,
                    "error": "REFEREE_FLAG",
                    "message": "Invalid Akka! (Higher cards exist)",
                    "intervention": {
                        "type": "INVALID_AKKA",
                        "playerIndex": player_index,
                        "message": "Cannot declare Akka! Higher cards are still in play."
                    }
                }

            # Valid Akka! — Write directly to the Pydantic model (single source of truth)
            self.game.state.akkaState = AkkaState(
                active=True,
                claimer=player.position,
                claimerIndex=player_index,
                suits=eligible,
                timestamp=time.time(),
            )

            logger.info(f"AKKA DECLARED by {player.position} for suits: {eligible}")
            return {"success": True, "akka_state": self.game.state.akkaState.model_dump()}

        except Exception as e:
            logger.error(f"Error in handle_akka: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": f"Internal error: {str(e)}"}
