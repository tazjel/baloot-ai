import logging
import random
from typing import Dict, Optional, Any

from game_engine.models.constants import GamePhase, BiddingPhase as BiddingState
from game_engine.logic.bidding_engine import BiddingEngine
# We might need to import Game dynamically or use TYPE_CHECKING to avoid circular imports
# from game_engine.logic.game import Game

logger = logging.getLogger(__name__)

class BiddingPhase:
    """
    Handles the BIDDING phase logic.
    Delegates to BiddingEngine but orchestrates the turn flow and state updates.
    """
    
    def __init__(self, game_instance):
        self.game = game_instance

    def handle_bid(self, player_index: int, action: str, suit: Optional[str] = None, reasoning: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a bid action from a player.
        """
        if self.game.phase not in [GamePhase.BIDDING.value, GamePhase.DOUBLING.value, GamePhase.VARIANT_SELECTION.value]:
            print(f"DEBUG: Phase Mismatch! Current={self.game.phase} Expected={[GamePhase.BIDDING.value, GamePhase.DOUBLING.value, GamePhase.VARIANT_SELECTION.value]}")
            return {'success': False, 'error': f"Not in bidding phase (Current: {self.game.phase})"}

        try:
            result = self.game.bidding_engine.process_bid(
                player_idx=player_index,
                action=action,
                suit=suit
            )
        except Exception as e:
             logger.error(f"Error in BiddingEngine: {e}")
             return {'success': False, 'error': str(e)}

        if result['success']:
            # Log reasoning/thought if provided (for AI)
            if reasoning and 'thoughts' in self.game.players[player_index].__dict__:
                 self.game.players[player_index].thoughts.append(f"Bid {action} {suit}: {reasoning}")
            
            # Handle Kawesh Redeal
            if result.get("action") == "REDEAL":
                logger.info(f"Kawesh Triggered. Result: {result}")

                if result.get("rotate_dealer"):
                    self.game.dealer_index = (self.game.dealer_index + 1) % 4

                # Redeal Flow
                self.game.reset_round_state()
                self.game.deal_initial_cards()

                # Re-initialize Engine
                self.game.bidding_engine = BiddingEngine(
                     dealer_index=self.game.dealer_index,
                     floor_card=self.game.floor_card,
                     players=self.game.players,
                     match_scores=self.game.match_scores
                )
                self.game.phase = GamePhase.BIDDING.value
                self.game.current_turn = self.game.bidding_engine.current_turn
                self.game.reset_timer()

                return result

            # Sync Game state with Engine state
            # This is a critical step: Game.bid dictionary must match Engine.current_bid
            self.game._sync_bid_state()
            
            # Check if bidding is complete
            # Check if bidding is complete (FINISHED only)
            engine_phase = self.game.bidding_engine.phase
            
            if engine_phase == BiddingState.FINISHED:
                winner = self.game.bidding_engine.get_winner()
                if winner:
                   self.game.complete_deal(winner['player_index'])
                else:
                   # All pass -> redeal
                   logger.info("All players passed. Redealing.")
                   self.game.reset_round_state()
                   self.game.deal_initial_cards()
            
            elif engine_phase in [BiddingState.DOUBLING, BiddingState.VARIANT_SELECTION]:
                 # Transition Game to Doubling if not already
                 if self.game.phase != GamePhase.DOUBLING.value:
                      self.game.phase = GamePhase.DOUBLING.value
                      logger.info("Game Phase Transition -> DOUBLING")
                 
                 # Continue turn cycle for Doubling
                 self.game.current_turn = self.game.bidding_engine.current_turn
                 self.game.reset_timer()
                 
            else:
                 # Standard Bidding (Round 1/2)
                 # Move to next turn
                 self.game.current_turn = self.game.bidding_engine.current_turn
                 self.game.reset_timer()
                 
        logger.info(f"BiddingPhase Handle Bid Result: {result}")
        return result

    def handle_double(self, player_index: int) -> Dict[str, Any]:
        """
        Process a Double/Redouble action.
        """
         # This logic is currently part of handle_bid in some flows, or separate. 
         # In the original game.py, handle_double is separate.
        return self.game.handle_double(player_index) # For now, delegate back or move logic here.
        # Ideally, we move the logic here.
