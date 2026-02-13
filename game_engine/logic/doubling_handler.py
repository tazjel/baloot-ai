"""
game_engine/logic/doubling_handler.py — Doubling Phase Handler
===============================================================

Extracted from bidding_engine.py. Handles the doubling chain
(Double → Triple → Four → Gahwa) and variant selection (Open/Closed).
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from game_engine.models.constants import BiddingPhase, BidType

if TYPE_CHECKING:
    from .bidding_engine import BiddingEngine

logger = logging.getLogger(__name__)


class DoublingHandler:
    """Manages the doubling chain and variant selection phases of bidding."""

    def __init__(self, engine: BiddingEngine):
        self.engine = engine

    def start(self):
        """Transition into the doubling phase after auction completes."""
        self.engine.phase = BiddingPhase.DOUBLING
        self.engine.doubling_history = []
        logger.info("Entering Doubling Phase.")
        # Start with Left Opponent (Bidder + 1)
        self.engine.current_turn = (self.engine.contract.bidder_idx + 1) % 4
        logger.info(f"Doubling Phase Started. First Turn: P{self.engine.current_turn}")

    def handle_bid(self, player_idx, action):
        """Handle a doubling-phase bid (PASS, DOUBLE, TRIPLE, FOUR, GAHWA)."""
        # Determine team relation to bidder
        p = next(p for p in self.engine.players if p.index == player_idx)
        taker = self.engine.players[self.engine.contract.bidder_idx]
        is_taker_team = (p.team == taker.team)

        current_level = self.engine.contract.level

        if action == "PASS":
            if self.engine.contract.type == BidType.HOKUM:
                # Coffee (Gahwa) forces OPEN variant — skip selection
                if self.engine.contract.level >= 100:
                    self.engine.contract.variant = "OPEN"
                    self.engine.phase = BiddingPhase.FINISHED
                    logger.info("Coffee (Gahwa): Variant forced to OPEN. Skipping selection.")
                    return {"success": True, "phase_change": "FINISHED"}
                self.engine.phase = BiddingPhase.VARIANT_SELECTION
                self.engine.current_turn = self.engine.contract.bidder_idx
                logger.info(f"Doubling Finished. Hokum Contract -> Variant Selection by P{self.engine.current_turn}")
                return {"success": True, "phase_change": "VARIANT_SELECTION"}
            else:
                self.engine.phase = BiddingPhase.FINISHED
                return {"success": True, "phase_change": "FINISHED"}

        # Logic Chain
        new_level = current_level
        if action == "DOUBLE":
            if is_taker_team: return {"error": "Cannot double own bid"}
            if current_level >= 2: return {"error": "Already doubled"}
            new_level = 2

            # Sun Firewall Rule
            if self.engine.contract.type == BidType.SUN:
                result = self._check_sun_firewall(player_idx)
                if result: return result

        elif action == "TRIPLE":
            if not is_taker_team: return {"error": "Only taking team can Triple"}
            if current_level != 2: return {"error": "Can only Triple a Double"}
            new_level = 3

        elif action == "FOUR":
            if is_taker_team: return {"error": "Only opponents can Four"}
            if current_level != 3: return {"error": "Can only Four a Triple"}
            new_level = 4

        elif action == "GAHWA":
            if not is_taker_team: return {"error": "Only taking team can Gahwa"}
            if current_level != 4: return {"error": "Can only Gahwa a Four"}
            new_level = 100  # Symbolic Max

        else:
            return {"error": f"Unknown doubling action {action}"}

        # Update State
        self.engine.contract.level = new_level
        self.engine.doubling_history.append({'action': action, 'player': player_idx})
        logger.info(f"Doubling Chain Updated: {action} by P{player_idx}. Level: {new_level}")

        return {"success": True, "status": "DOUBLED", "level": new_level}

    def handle_variant(self, player_idx, action):
        """Handle OPEN/CLOSED selection by Buyer."""
        if player_idx != self.engine.contract.bidder_idx:
            return {"error": "Only Buyer can choose Variant"}

        if action not in ["OPEN", "CLOSED"]:
            return {"error": "Invalid Variant (Must be OPEN or CLOSED)"}

        self.engine.contract.variant = action
        self.engine.phase = BiddingPhase.FINISHED
        logger.info(f"Variant Selected: {action}")
        return {"success": True, "phase_change": "FINISHED"}

    def _check_sun_firewall(self, doubler_idx):
        """Sun doubling allowed ONLY if bidder score > 100 and doubler score < 100."""
        p = next(p for p in self.engine.players if p.index == doubler_idx)
        bidder_pos = self.engine.players[self.engine.contract.bidder_idx].position
        doubler_pos = p.position

        bidder_team = 'us' if bidder_pos in ['Bottom', 'Top'] else 'them'
        doubler_team = 'us' if doubler_pos in ['Bottom', 'Top'] else 'them'

        bidder_score = self.engine.match_scores.get(bidder_team, 0)
        doubler_score = self.engine.match_scores.get(doubler_team, 0)

        if not (bidder_score >= 100 and doubler_score < 100):
            return {"error": f"Sun Double Rejected. Firewall Active. Scores: {bidder_team}={bidder_score}, {doubler_team}={doubler_score}"}
        return None
