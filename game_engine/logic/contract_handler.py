"""
game_engine/logic/contract_handler.py — Contract Bidding Handler
=================================================================

Extracted from bidding_engine.py. Handles the core auction logic:
contract bids (Hokum/Sun), Gablak windows, pass handling, turn
advancement, and bid validation.
"""

from __future__ import annotations
import time
import logging
from typing import TYPE_CHECKING

from game_engine.models.constants import BiddingPhase, BidType

if TYPE_CHECKING:
    from .bidding_engine import BiddingEngine

logger = logging.getLogger(__name__)


class ContractHandler:
    """Manages the core auction: bids, passes, Gablak, turn rotation."""

    def __init__(self, engine: BiddingEngine):
        self.engine = engine

    # ── Priority helper ──────────────────────────────────────────────

    def get_priority(self, player_idx):
        return self.engine.priority_queue.index(player_idx)

    # ── Ashkal eligibility ───────────────────────────────────────────

    def is_ashkal_eligible(self, player_idx):
        """Ashkal allowed for Dealer and Left-of-Dealer."""
        is_dealer = (player_idx == self.engine.dealer_index)
        is_left = (player_idx == (self.engine.dealer_index + 3) % 4)
        return is_dealer or is_left

    # ── Contract Bid (Main auction logic) ────────────────────────────

    def handle_bid(self, player_idx, action, suit):
        """Handle a contract bid during ROUND_1, ROUND_2, or GABLAK_WINDOW."""
        engine = self.engine

        # --- CHECK 1: Higher Bids ---
        if engine.contract.type == BidType.SUN:
            if action == "HOKUM":
                return {"error": "Cannot bid Hokum over Sun"}

        if engine.contract.type == BidType.HOKUM:
            if action == "HOKUM":
                if engine.phase != BiddingPhase.GABLAK_WINDOW:
                    # STRICT PRIORITY CHECK for hijacking
                    current_bidder_prio = self.get_priority(engine.contract.bidder_idx)
                    my_prio = self.get_priority(player_idx)

                    if my_prio >= current_bidder_prio:
                        return {"error": "Hokum bid already exists. Only Sun (or Higher Priority) can hijack."}
                    else:
                        logger.info(f"Priority Hijack! P{player_idx} (Prio {my_prio}) overrides P{engine.contract.bidder_idx} (Prio {current_bidder_prio}) with HOKUM.")

        # --- GABLAK WINDOW Handling ---
        if engine.phase == BiddingPhase.GABLAK_WINDOW:
            result = self._handle_gablak_action(player_idx, action)
            if result is not None:
                return result

        # B. Turn Order Logic
        if engine.phase != BiddingPhase.GABLAK_WINDOW:
            if player_idx != engine.current_turn:
                return {"error": "Not your turn"}

        # --- Priority Analysis ---
        my_prio = self.get_priority(player_idx)
        better_player_exists = self._check_better_player_exists(my_prio)

        # --- Execution Logic ---
        if action == "PASS":
            return self.handle_pass(player_idx)

        # Validate Bid constraints (Suit, Ace Rule, etc)
        valid, msg = self.validate_constraints(player_idx, action, suit)
        if not valid: return {"error": msg}

        # --- GABLAK TRIGGER ---
        is_sun = (action in ["SUN", "ASHKAL"])

        if better_player_exists:
            return self._trigger_gablak(player_idx, action, suit)
        else:
            # I am the highest priority available.
            if engine.contract.type == BidType.HOKUM and is_sun:
                logger.info("Sun Hijack Confirmation!")

            self.set_contract(player_idx, action, suit)

            if is_sun:
                self._finalize_auction()
                return {"success": True, "phase_change": "DOUBLING"}

            self.advance_turn()
            return {"success": True}

    # ── Gablak sub-handlers ──────────────────────────────────────────

    def _handle_gablak_action(self, player_idx, action):
        """Handle bids/passes inside the Gablak window. Returns None to continue normal flow."""
        engine = self.engine

        # Check Timer
        if time.time() - engine.gablak_timer_start > engine.GABLAK_DURATION:
            logger.info("Gablak Window Timeout. Finalizing tentative bid.")
            self.finalize_tentative()
            return {"success": True, "status": "GABLAK_TIMEOUT", "message": "Gablak window expired. Bid finalized."}

        tentative_idx = engine.tentative_bid['bidder']

        # If action is PASS: waive right
        if action == "PASS":
            if self.get_priority(player_idx) == engine.gablak_current_prio:
                engine.gablak_current_prio += 1

            if engine.gablak_current_prio >= self.get_priority(tentative_idx):
                logger.info("All higher priority players waived Gablak. Finalizing.")
                self.finalize_tentative()
                return {"success": True, "status": "GABLAK_COMPLETED"}

            return {"success": True, "status": "WAIVED_GABLAK"}

        # If it's a BID (Hijack):
        if self.get_priority(player_idx) >= self.get_priority(tentative_idx):
            return {"error": "Not enough priority to Gablak/Steal"}

        return None  # Continue to normal bid processing

    def _trigger_gablak(self, player_idx, action, suit):
        """Open a Gablak window for higher-priority players."""
        engine = self.engine

        if engine.phase != BiddingPhase.GABLAK_WINDOW:
            engine.pre_gablak_phase = engine.phase

        engine.tentative_bid = {
            'type': action,
            'bidder': player_idx,
            'suit': suit,
            'timestamp': time.time()
        }
        engine.phase = BiddingPhase.GABLAK_WINDOW
        engine.gablak_timer_start = time.time()
        engine.gablak_current_prio = 0  # Start asking from Priority 0

        logger.info(f"Gablak Triggered by P{player_idx}. Waiting for higher priority.")
        return {"success": True, "status": "GABLAK_TRIGGERED", "wait": engine.GABLAK_DURATION}

    def _check_better_player_exists(self, my_prio):
        """Check if any un-passed player with better priority exists."""
        engine = self.engine
        for i in range(my_prio):
            p_chk = engine.priority_queue[i]

            has_passed = False
            if engine.phase == BiddingPhase.ROUND_2:
                if p_chk in engine.passed_players_r2 or (p_chk in engine.passed_players_r1):
                    has_passed = True
            else:
                if p_chk in engine.passed_players_r1:
                    has_passed = True

            if not has_passed:
                return True
        return False

    # ── Finalization ─────────────────────────────────────────────────

    def finalize_tentative(self):
        """Called when Gablak timer expires or all competitors waive."""
        engine = self.engine
        if not engine.tentative_bid: return

        tb = engine.tentative_bid
        self.set_contract(tb['bidder'], tb['type'], tb['suit'])

        is_sun = (tb['type'] in ["SUN", "ASHKAL"])
        if is_sun:
            self._finalize_auction()
        else:
            engine.phase = engine.pre_gablak_phase or BiddingPhase.ROUND_1

        engine.tentative_bid = None
        self.advance_turn()

    def _finalize_auction(self):
        """Called when a contract is final (Sun or Hokum after passes)."""
        logger.info(f"Auction Finalized. Contract: {self.engine.contract}")
        self.engine._doubling.start()

    # ── Pass handling ────────────────────────────────────────────────

    def handle_pass(self, player_idx):
        """Handle a player passing their bid turn."""
        engine = self.engine

        if engine.phase == BiddingPhase.ROUND_1:
            engine.passed_players_r1.add(player_idx)
        elif engine.phase == BiddingPhase.ROUND_2:
            engine.passed_players_r2.add(player_idx)

        if engine.phase == BiddingPhase.GABLAK_WINDOW:
            return {"error": "Cannot pass during Gablak (Action required is Steal or Ignore)"}

        self.advance_turn()
        return {"success": True}

    # ── Turn management ──────────────────────────────────────────────

    def advance_turn(self):
        """Rotate to the next player, handle round transitions."""
        engine = self.engine
        next_turn = (engine.current_turn + 1) % 4

        # Check Round Transitions
        if next_turn == (engine.dealer_index + 1) % 4:
            # Full Circle Completed
            if engine.contract.type:
                # Contract Finalized!
                engine._doubling.start()
                return

            if engine.phase == BiddingPhase.ROUND_1:
                engine.phase = BiddingPhase.ROUND_2
                logger.info("Transition to Round 2")
            elif engine.phase == BiddingPhase.ROUND_2:
                engine.phase = BiddingPhase.FINISHED

        engine.current_turn = next_turn

    # ── Bid Validation ───────────────────────────────────────────────

    def validate_constraints(self, player_idx, action, suit):
        """Validate bid constraints based on round, suit, and hierarchy."""
        engine = self.engine

        # Ashkal checks (unified for R1 and R2)
        if action == "ASHKAL":
            if engine.floor_card.rank == 'A':
                return False, "Ashkal banned on Ace"
            if not self.is_ashkal_eligible(player_idx):
                return False, "Not eligible for Ashkal (Position)"

        # Round 1 Constraints
        if engine.phase == BiddingPhase.ROUND_1:
            if action == "HOKUM":
                if suit != engine.floor_card.suit:
                    return False, "Round 1 Hokum must be floor suit"

        # Round 2 Constraints
        if engine.phase == BiddingPhase.ROUND_2:
            if action == "HOKUM":
                if suit == engine.floor_card.suit:
                    return False, "Cannot bid floor suit in Round 2"

        # Hierarchy Constraint
        if engine.contract.type == BidType.SUN:
            return False, "Cannot bid lower than Sun"

        return True, "OK"

    # ── Contract setter ──────────────────────────────────────────────

    def set_contract(self, player_idx, action, suit):
        """Set the active contract on the engine."""
        engine = self.engine

        if action == "ASHKAL":
            partner_idx = (player_idx + 2) % 4
            engine.contract.type = BidType.SUN
            engine.contract.bidder_idx = partner_idx
            engine.contract.suit = None
            engine.contract.is_ashkal = True
        else:
            engine.contract.type = BidType(action)
            engine.contract.bidder_idx = player_idx
            engine.contract.suit = suit

        # Track Round
        active_phase = engine.pre_gablak_phase if engine.phase == BiddingPhase.GABLAK_WINDOW else engine.phase
        engine.contract.round = 1 if active_phase == BiddingPhase.ROUND_1 else 2

        engine.has_bid_occurred = True
