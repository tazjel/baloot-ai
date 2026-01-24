
import time
import logging
from enum import Enum, auto
from game_engine.logic.utils import is_kawesh_hand
from game_engine.models.constants import BiddingPhase, BidType

# Configure Logging
logger = logging.getLogger(__name__)



class ContractState:
    def __init__(self):
        self.type = None # HOKUM or SUN
        self.suit = None # If HOKUM
        self.bidder_idx = None
        self.team = None # 'us' or 'them'
        self.level = 1 # 1=Normal, 2=Doubled, 3=Triple, 4=Four, 100=Gahwa
        self.variant = None # 'OPEN' or 'CLOSED' for Doubled Hokum
        self.is_ashkal = False
        self.round = 1 # 1 or 2 (Track when bid happened)

    def __repr__(self):
        return f"<Contract {self.type} ({self.suit}) by {self.bidder_idx} Lvl:{self.level} {self.variant}>"

class BiddingEngine:
    def __init__(self, dealer_index, floor_card, players, match_scores):
        self.dealer_index = dealer_index
        self.floor_card = floor_card
        self.players = players # List of Player objects (needed for names/teams)
        self.match_scores = match_scores # {'us': int, 'them': int}
        
        # State
        self.phase = BiddingPhase.ROUND_1
        self.current_turn = (dealer_index + 1) % 4
        self.priority_queue = [(dealer_index + 1) % 4, (dealer_index + 2) % 4, (dealer_index + 3) % 4, dealer_index]
        
        self.contract = ContractState()
        self.tentative_bid = None # {type, bidder, suit, timestamp} - Before GABLAK finalization
        self.gablak_timer_start = 0
        self.gablak_current_prio = 0 # Sequential tracking for Headless/Fast-path
        self.pre_gablak_phase = None # Track if we were in R1 or R2
        self.GABLAK_DURATION = 5 # seconds
        
        self.passed_players_r1 = set()
        self.passed_players_r2 = set() # Track for Round 2 end
        self.doubling_history = [] # For validating chain order
        self.has_bid_occurred = False # Track for Dealer Rotation (was Antigravity)
        
        logger.info(f"BiddingEngine Initialized. Dealer: {dealer_index}. Priority: {self.priority_queue}")

    def get_state(self):
        return {
            "phase": self.phase.value,
            "currentTurn": self.current_turn,
            "contract": {
                "type": self.contract.type.value if self.contract.type else None,
                "suit": self.contract.suit,
                "bidder": self.players[self.contract.bidder_idx].position if self.contract.bidder_idx is not None else None,
                "level": self.contract.level,
                "variant": self.contract.variant,
                "isAshkal": self.contract.is_ashkal,
                "round": self.contract.round
            },
            "tentativeBid": self.tentative_bid,
            "gablakActive": (self.phase == BiddingPhase.GABLAK_WINDOW),
            "floorCard": self.floor_card.to_dict() if self.floor_card else None
        }

    def get_current_actor(self):
        """Returns the player whose turn it is, accounting for Gablak windows."""
        if self.phase == BiddingPhase.GABLAK_WINDOW:
             if self.gablak_current_prio < len(self.priority_queue):
                  return self.priority_queue[self.gablak_current_prio]
        return self.current_turn

    def process_bid(self, player_idx, action, suit=None, variant=None):
        logger.info(f"Process Bid: P{player_idx} wants {action} (Suit: {suit}, Phase: {self.phase.value})")
        
        # 1. State Verification
        if self.phase == BiddingPhase.FINISHED:
             return {"error": "Bidding is finished"}
        
        # [KAWESH INTERCEPT]
        # Kawesh is a "super-action" valid at any time before playing Phase
        if action == "KAWESH":
             return self._handle_kawesh(player_idx)
        
        # 2. Phase Delegation
        if self.phase in [BiddingPhase.ROUND_1, BiddingPhase.ROUND_2, BiddingPhase.GABLAK_WINDOW]:
             result = self._handle_contract_bid(player_idx, action, suit)
        elif self.phase == BiddingPhase.DOUBLING:
             result = self._handle_doubling_bid(player_idx, action)
        elif self.phase == BiddingPhase.VARIANT_SELECTION:
             result = self._handle_variant_selection(player_idx, action)
        else:
             return {"error": "Invalid internal state"}
        
        return result

    def _handle_kawesh(self, player_idx):
        """
        Handle Kawesh declaration.
        Rules:
        1. Hand must be ONLY 7, 8, 9 (Zero points). A, K, Q, J, 10 forbidden.
        2. Pre-Bid: Redeal, SAME Dealer.
        3. Post-Bid: Redeal, ROTATE Dealer (Dealer Rotation).
        """
        player = next(p for p in self.players if p.index == player_idx)
        
        # 1. Validate Hand
        if not is_kawesh_hand(player.hand):
             return {"error": "Cannot call Kawesh with points (A, K, Q, J, 10) in hand"}
        
        # 2. Valid Kawesh - Check Timing
        if self.has_bid_occurred:
             # Post-Bid -> Dealer Rotation
             logger.info(f"Post-Bid Kawesh by P{player_idx}. Dealer Rotates.")
             return {"success": True, "action": "REDEAL", "rotate_dealer": True}
        else:
             # Pre-Bid -> Hard Reset
             logger.info(f"Pre-Bid Kawesh by P{player_idx}. Dealer Retained.")
             return {"success": True, "action": "REDEAL", "rotate_dealer": False}


    def _handle_contract_bid(self, player_idx, action, suit):
        # --- CHECK 1: Higher Bids ---
        # "Is this bid lower than an existing bid? (e.g., trying to bid Hokum when Sun is active). → Reject."
        if self.contract.type == BidType.SUN:
             if action == "HOKUM":
                  return {"error": "Cannot bid Hokum over Sun"}
             # Same type (Sun/Ashkal over Sun) only allowed if higher priority (Gablak/Hijack)
             # This is handled by the hijack check below.
        
        if self.contract.type == BidType.HOKUM:
             if action == "HOKUM":
                  # Only allowed via Gablak (intercepted at start of method)
                  if self.phase != BiddingPhase.GABLAK_WINDOW:
                       return {"error": "Hokum bid already exists. Only Sun can hijack."}


        # --- GABLAK WINDOW Handling ---
        if self.phase == BiddingPhase.GABLAK_WINDOW:
             # Check Timer
             if time.time() - self.gablak_timer_start > self.GABLAK_DURATION:
                  # Timeout! The tentative bid wins.
                  # THIS player missed the window (unless they are the tentative bidder confirming?)
                  logger.info("Gablak Window Timeout. Finalizing tentative bid.")
                  self._finalize_tentative_bid()
                  # Return SUCCESS so game.py syncs the new state (Contract Finalized, Phase changed, etc)
                  return {"success": True, "status": "GABLAK_TIMEOUT", "message": "Gablak window expired. Bid finalized."}
             
             # Deterministic Sequential Logic:
             # Only the "Current Window Turn" or someone HIGHER priority can interject.
             tentative_idx = self.tentative_bid['bidder']
             
             # If action is PASS: They waive their right.
             if action == "PASS":
                  # Is this player the one we were waiting for (highest priority left)?
                  if self._get_priority(player_idx) == self.gablak_current_prio:
                       self.gablak_current_prio += 1
                  
                  # If we reached the tentative bidder, they have no more competitors
                  if self.gablak_current_prio >= self._get_priority(tentative_idx):
                       logger.info("All higher priority players waived Gablak. Finalizing.")
                       self._finalize_tentative_bid()
                       return {"success": True, "status": "GABLAK_COMPLETED"}
                       
                  return {"success": True, "status": "WAIVED_GABLAK"}
             
             # If it's a BID (Hijack):
             if self._get_priority(player_idx) >= self._get_priority(tentative_idx):
                  return {"error": "Not enough priority to Gablak/Steal"}
        
        # B. Turn Order Logic
        if self.phase != BiddingPhase.GABLAK_WINDOW:
             if player_idx != self.current_turn:
                  return {"error": "Not your turn"}

        # --- CHECK 2: Gablak Loop / Turn Order ---
        # "If (P_current) is NOT Priority_List (not the First Player), terminate?"
        # Wait, the logic is:
        # If Player X wants to bid. Check if anyone with Higher Priority exists.
        
        my_prio = self._get_priority(player_idx)
        
        # Check if anyone with BETTER priority is "Available" (Has not passed current round)
        better_player_exists = False
        
        # Range 0 to my_prio - 1
        for i in range(my_prio):
             p_chk = self.priority_queue[i]
             
             # Pass Check
             has_passed = False
             if self.phase == BiddingPhase.ROUND_2:
                  if p_chk in self.passed_players_r2 or (p_chk in self.passed_players_r1): 
                       # Rule: "If Player_A.Passed_Round1 == True, they cannot use Gablak in R2"
                       # Wait, if they passed R1, can they bid Sun in R2 normally?
                       # "unless they are upgrading it to Sun."
                       # If I bid Sun, they can still steal if they upgrade?
                       # Let's stick to: "If passed R1, cannot steal HOKUM". 
                       # But here checking existence.
                       has_passed = True # Assume they are out of the picture for specific bid types?
                       # If I am bidding SUN, passed players CANNOT steal unless they didn't pass Sun?
                       # Passing R1 usually implies passing everything for R1.
                       pass
             else:
                  if p_chk in self.passed_players_r1: has_passed = True
             
             if not has_passed:
                  better_player_exists = True
                  break
        
        # --- Execution Logic ---
        
        if action == "PASS":
             return self._handle_pass(player_idx)

        # Validate Bid constraints (Suit, Ace Rule, etc)
        valid, msg = self._validate_bid_constraints(player_idx, action, suit)
        if not valid: return {"error": msg}

        # --- GABLAK TRIGGER ---
        # If better players exist, we cannot finalize immediately.
        # "Trigger Gablak Opportunity"
        
        # Ace Exception: "If Priority_List bids Sun... No Gablak is possible."
        # If I am Priority 0 (First), no one is better.
        # If I am NOT Priority 0, but I bid Sun on Ace?
        # Rule check: "If Priority_List [0] bids Sun...". 
        # Actually, if I am Prio 3, and Prio 0,1,2 passed -> I am effectively Prio 0 for now.
        # The `better_player_exists` check handles this! 
        # If Prio 0 passed, `better_player_exists` is False for Prio 1.
        
        is_sun = (action in ["SUN", "ASHKAL"])
        
        if better_player_exists:
             # We must PAUSE and ask higher priority players.
             if self.phase == BiddingPhase.GABLAK_WINDOW:
                  # Creating a window INSIDE a window? 
                  # Usually: hijack the current window.
                  # If P3 bids (Window for P1, P2). P2 interrupts. 
                  # P2 is better than P3. But P1 is better than P2.
                  # So we reset window for P1? Yes.
                  pass
             
             if self.phase != BiddingPhase.GABLAK_WINDOW:
                  self.pre_gablak_phase = self.phase

             self.tentative_bid = {
                 'type': action, 
                 'bidder': player_idx, 
                 'suit': suit, 
                 'timestamp': time.time()
             }
             self.phase = BiddingPhase.GABLAK_WINDOW
             self.gablak_timer_start = time.time()
             self.gablak_current_prio = 0 # Start asking from Priority 0
             
             logger.info(f"Gablak Triggered by P{player_idx}. Waiting for higher priority.")
             return {"success": True, "status": "GABLAK_TRIGGERED", "wait": self.GABLAK_DURATION}
             
        else:
             # I am the highest priority available.
             # "Sun > Hokum" logic (Hijack) handled by overwriting.
             
             # If I bid Sun, and previous was Hokum?
             if self.contract.type == BidType.HOKUM and is_sun:
                  logger.info("Sun Hijack Confirmation!")
                  
             self._set_contract(player_idx, action, suit)
             
             # Game Start Logic
             # "If Sun ... End Bidding Phase Immediately" (Unless Ace Ashkal exception? No Ashkal is Sun).
             # If Hokum... "Continue asking".
             
             if is_sun:
                  self._finalize_auction()
                  return {"success": True, "phase_change": "DOUBLING"}
             
             # If Hokum, we continue.
             # But if I am Prio 0 and I bid Hokum?
             # Others can still bid SUN! (Sun > Hokum always).
             # So we do NOT end bidding on Hokum.
             
             self._advance_turn()
             return {"success": True}

    def _finalize_tentative_bid(self):
        """Called when Gablak timer expires."""
        if not self.tentative_bid: return
        
        tb = self.tentative_bid
        self._set_contract(tb['bidder'], tb['type'], tb['suit'])
        
        # Check if we should end
        is_sun = (tb['type'] in ["SUN", "ASHKAL"])
        if is_sun:
             self._finalize_auction()
        else:
             # Restore the round we were in
             self.phase = self.pre_gablak_phase or BiddingPhase.ROUND_1
             
        self.tentative_bid = None
        
        # Advance turn from the bidder, which correctly triggers end-of-auction if circle complete
        self._advance_turn()

    def _handle_pass(self, player_idx):
        if self.phase == BiddingPhase.ROUND_1:
             self.passed_players_r1.add(player_idx)
        elif self.phase == BiddingPhase.ROUND_2:
             self.passed_players_r2.add(player_idx)
             
        # If Gablak Window?
        if self.phase == BiddingPhase.GABLAK_WINDOW:
             return {"error": "Cannot pass during Gablak (Action required is Steal or Ignore)"}

        # Check for Round End / Game Over
        # Logic: If 3 passes after a Bid? Or 4 passes total?
        
        # Case 1: Contract exists (Hokum).
        if self.contract.type == BidType.HOKUM:
             # If everyone else passed Sun opportunity?
             # Simplified: If turn returns to Bidder?
             pass
             
        # Case 2: No Contract.
        # If 4 passes in R1 -> Go R2.
        # If 4 passes in R2 -> Redeal.
        
        self._advance_turn()
        return {"success": True}

    def _advance_turn(self):
        # Rotate to next player in Priority Queue sequence or logical circle?
        # Usually circle: (Current + 1) % 4
        # But skip if they already passed?
        
        # Simple cyclic for now
        next_turn = (self.current_turn + 1) % 4
        
        # Check Round Transitions
        if next_turn == (self.dealer_index + 1) % 4:
             # Full Circle Completed
             if self.contract.type:
                  # Contract Finalized!
                  self._start_doubling_phase()
                  return
             
             if self.phase == BiddingPhase.ROUND_1:
                  self.phase = BiddingPhase.ROUND_2
                  logger.info("Transition to Round 2")
             elif self.phase == BiddingPhase.ROUND_2:
                  # All passed R2 -> FINISHED (Redeal needed)
                  self.phase = BiddingPhase.FINISHED
                  # Caller handles Redeal logic
                  
        self.current_turn = next_turn

    def _validate_bid_constraints(self, player_idx, action, suit):
        # 1. Round 1 Constraints
        if self.phase == BiddingPhase.ROUND_1:
             if action == "HOKUM":
                  if suit != self.floor_card.suit:
                       return False, "Round 1 Hokum must be floor suit"
             elif action == "ASHKAL":
                  # Ashkal allowed? Check Ace Rule
                  if self.floor_card.rank == 'A':
                       return False, "Ashkal banned on Ace"
                  if not self._is_ashkal_eligible(player_idx):
                       return False, "Not eligible for Ashkal (Position)"

        # 2. Round 2 Constraints
        if self.phase == BiddingPhase.ROUND_2:
             if action == "ASHKAL":
                  if self.floor_card.rank == 'A':
                       return False, "Ashkal banned on Ace"
                  if not self._is_ashkal_eligible(player_idx):
                       return False, "Not eligible for Ashkal (Position)"

             if action == "HOKUM":
                  if suit == self.floor_card.suit:
                       return False, "Cannot bid floor suit in Round 2"
                       
        # 3. Hierarchy Constraint
        # Cannot bid Hokum if Sun is active (Already handled by hijack check mostly, but sanity check)
        if self.contract.type == BidType.SUN:
             return False, "Cannot bid lower than Sun"
             
        return True, "OK"

    def _set_contract(self, player_idx, action, suit):
        if action == "ASHKAL":
             # Partner takes it as Sun!
             partner_idx = (player_idx + 2) % 4
             self.contract.type = BidType.SUN
             self.contract.bidder_idx = partner_idx
             self.contract.suit = None # Sun has no suit
             self.contract.is_ashkal = True
        else:
             self.contract.type = BidType(action)
             self.contract.bidder_idx = player_idx
             self.contract.suit = suit
        
        # Track Round
        active_phase = self.pre_gablak_phase if self.phase == BiddingPhase.GABLAK_WINDOW else self.phase
        self.contract.round = 1 if active_phase == BiddingPhase.ROUND_1 else 2
        
        # Mark that a bid has occurred (for Kawesh Antigravity logic)
        self.has_bid_occurred = True

    def _finalize_auction(self):
        """Called when a contract is final (Sun or Hokum after passes)."""
        logger.info(f"Auction Finalized. Contract: {self.contract}")
        self._start_doubling_phase()

    def _start_doubling_phase(self):
        self.phase = BiddingPhase.DOUBLING
        self.doubling_history = []
        logger.info("Entering Doubling Phase.")
        # Identify who can start doubling?
        # Any opponent of the Taker team.
        # Strict turn: Start with Left Opponent (Bidder + 1)
        self.current_turn = (self.contract.bidder_idx + 1) % 4
        logger.info(f"Doubling Phase Started. First Turn: P{self.current_turn}")

    # --- DOUBLING LOGIC ---
    def _handle_doubling_bid(self, player_idx, action):
        # Valid actions: PASS, DOUBLE, TRIPLE, FOUR, GAHWA
        
        # Determine team relation to bidder
        p = next(p for p in self.players if p.index == player_idx)
        taker = self.players[self.contract.bidder_idx]
        is_taker_team = (p.team == taker.team)
        
        current_level = self.contract.level
        
        if action == "PASS":
             # If PASS, we need to know if EVERYONE passed this opportunity?
             # For simplicity: If Opponent passes Double, they waive right.
             # If Taker passes Triple, they waive right.
             # We need a strict turn state here too?
             # "Challenge Mode" implies async, but first valid claim wins.
             # If both opponents pass, game starts.
             # Let's say: If action is PASS, we treat it as "Ready to Start".
             # If all players (or relevant team) pass...
             
             # If all players (or relevant team) pass...
             
             if self.contract.type == BidType.HOKUM:
                  self.phase = BiddingPhase.VARIANT_SELECTION
                  self.current_turn = self.contract.bidder_idx
                  logger.info(f"Doubling Finished. Hokum Contract -> Variant Selection by P{self.current_turn}")
                  return {"success": True, "phase_change": "VARIANT_SELECTION"}
             else:
                  self.phase = BiddingPhase.FINISHED
                  return {"success": True, "phase_change": "FINISHED"}

        # Logic Chain
        new_level = current_level
        if action == "DOUBLE": # Dobl
            if is_taker_team: return {"error": "Cannot double own bid"}
            if current_level >= 2: return {"error": "Already doubled"}
            new_level = 2
             
            # Sun Firewall Rule
            # Sun doubling allowed ONLY if:
            # 1. Bidder Team Score > 100
            # 2. Doubler Team Score < 100
            if self.contract.type == BidType.SUN:
                bidder_pos = self.players[self.contract.bidder_idx].position
                doubler_pos = p.position
                  
                # Identify teams
                bidder_team = 'us' if bidder_pos in ['Bottom', 'Top'] else 'them'
                doubler_team = 'us' if doubler_pos in ['Bottom', 'Top'] else 'them'
                  
                bidder_score = self.match_scores.get(bidder_team, 0)
                doubler_score = self.match_scores.get(doubler_team, 0)
                  
                if not (bidder_score > 100 and doubler_score < 100):
                    return {"error": f"Sun Double Rejected. Firewall Active. Scores: {bidder_team}={bidder_score}, {doubler_team}={doubler_score}"}
 
            # Hokum Variant (Open/Closed)
            # DECOUPLED: Double is now clean. Variant chosen later.
            if self.contract.type == BidType.HOKUM:
                # Just set level. Variant selection comes after doubling chain ends.
                pass

        elif action == "TRIPLE": # Khamsin
             if not is_taker_team: return {"error": "Only taking team can Triple"}
             if current_level != 2: return {"error": "Can only Triple a Double"}
             new_level = 3

        elif action == "FOUR": # Raba'a
             if is_taker_team: return {"error": "Only opponents can Four"}
             if current_level != 3: return {"error": "Can only Four a Triple"}
             new_level = 4

        elif action == "GAHWA": # Coffee (Match Win)
             # "Only Taker's team can reply" to Raba'a?
             # Rules say: "Gahwa (Coffee): Only the Taker's team can reply."
             if not is_taker_team: return {"error": "Only taking team can Gahwa"}
             if current_level != 4: return {"error": "Can only Gahwa a Four"}
             new_level = 100 # Symbolic Max

        else:
             return {"error": f"Unknown doubling action {action}"}

        # Update State
        self.contract.level = new_level
        self.doubling_history.append({'action': action, 'player': player_idx})
        logger.info(f"Doubling Chain Updated: {action} by P{player_idx}. Level: {new_level}")
        
        return {"success": True, "status": "DOUBLED", "level": new_level}

    def _handle_variant_selection(self, player_idx, action):
        """Handle OPEN/CLOSED selection by Buyer."""
        if player_idx != self.contract.bidder_idx:
             return {"error": "Only Buyer can choose Variant"}
        
        if action not in ["OPEN", "CLOSED"]:
             return {"error": "Invalid Variant (Must be OPEN or CLOSED)"}
            
        self.contract.variant = action
        self.phase = BiddingPhase.FINISHED
        logger.info(f"Variant Selected: {action}")
        return {"success": True, "phase_change": "FINISHED"}

    def _is_ashkal_eligible(self, player_idx):
        # Ashkal only allowed for Dealer (Prio 3) and Left of Dealer (Prio 2) ??
        # Or generally high priority?
        # User prompt said: "If Player calls Ashkal... specific bid type... in Round 2".
        # It didn't specify position restriction in the prompt, but standard rules usually imply it.
        # Let's keep it permissive if unsure, or restrict as per previous code.
        # Strict rule: Ashkal is usually for the Dealer and their partner in some variants, 
        # or simply "Partner of the one who passed" - wait.
        # Let's trust the previous implementation of specific indices for now.
        is_dealer = (player_idx == self.dealer_index)
        is_left = (player_idx == (self.dealer_index + 3) % 4)
        return is_dealer or is_left

    def _get_priority(self, player_idx):
        return self.priority_queue.index(player_idx)
