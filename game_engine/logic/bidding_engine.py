
import time
import logging
from enum import Enum, auto
from typing import Optional
from pydantic import BaseModel, ConfigDict
from game_engine.logic.utils import is_kawesh_hand
from game_engine.models.constants import BiddingPhase, BidType

# Configure Logging
logger = logging.getLogger(__name__)



class ContractState(BaseModel):
    """Pydantic model for bidding contract state. Replaces the old raw-attribute class."""
    model_config = ConfigDict(extra='forbid')

    type: Optional[BidType] = None       # HOKUM or SUN
    suit: Optional[str] = None           # If HOKUM (e.g. '♠')
    bidder_idx: Optional[int] = None
    team: Optional[str] = None           # 'us' or 'them'
    level: int = 1                       # 1=Normal, 2=Doubled, 3=Triple, 4=Four, 100=Gahwa
    variant: Optional[str] = None        # 'OPEN' or 'CLOSED' for Doubled Hokum
    is_ashkal: bool = False
    round: int = 1                       # 1 or 2 (Track when bid happened)

    def to_dict(self) -> dict:
        """Serialize to dict (JSON-safe)."""
        return self.model_dump(mode='json')

    @classmethod
    def from_dict(cls, data: dict) -> 'ContractState':
        """Deserialize from dict."""
        return cls(**data)

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
        
        # Phase handlers
        from .contract_handler import ContractHandler
        from .doubling_handler import DoublingHandler
        self._contract = ContractHandler(self)
        self._doubling = DoublingHandler(self)
        
        logger.info(f"BiddingEngine Initialized. Dealer: {dealer_index}. Priority: {self.priority_queue}")

    # ── Serialization ────────────────────────────────────────────────
    def to_dict(self) -> dict:
        """Serialize engine state for Redis persistence."""
        return {
            'dealer_index': self.dealer_index,
            'floor_card': self.floor_card.to_dict() if self.floor_card else None,
            'match_scores': self.match_scores,
            'phase': self.phase.value,
            'current_turn': self.current_turn,
            'priority_queue': self.priority_queue,
            'contract': self.contract.to_dict(),
            'tentative_bid': self.tentative_bid,
            'gablak_timer_start': self.gablak_timer_start,
            'gablak_current_prio': self.gablak_current_prio,
            'pre_gablak_phase': self.pre_gablak_phase.value if self.pre_gablak_phase else None,
            'GABLAK_DURATION': self.GABLAK_DURATION,
            'passed_players_r1': list(self.passed_players_r1),
            'passed_players_r2': list(self.passed_players_r2),
            'doubling_history': self.doubling_history,
            'has_bid_occurred': self.has_bid_occurred,
        }

    @classmethod
    def from_dict(cls, data: dict, players) -> 'BiddingEngine':
        """Reconstruct engine from serialized dict + live player objects."""
        if not players or len(players) != 4:
            raise ValueError(f"BiddingEngine.from_dict requires exactly 4 players, got {len(players) if players else 0}")

        from game_engine.models.card import Card
        floor_card_d = data.get('floor_card')
        floor_card = Card(floor_card_d['suit'], floor_card_d['rank']) if floor_card_d else None

        engine = cls.__new__(cls)
        engine.dealer_index = data['dealer_index']
        engine.floor_card = floor_card
        engine.players = players
        engine.match_scores = data['match_scores']
        engine.phase = BiddingPhase(data['phase'])
        engine.current_turn = data['current_turn']
        engine.priority_queue = data['priority_queue']
        engine.contract = ContractState.from_dict(data['contract'])
        engine.tentative_bid = data.get('tentative_bid')
        engine.gablak_timer_start = data.get('gablak_timer_start', 0)
        engine.gablak_current_prio = data.get('gablak_current_prio', 0)
        pre_phase = data.get('pre_gablak_phase')
        engine.pre_gablak_phase = BiddingPhase(pre_phase) if pre_phase else None
        engine.GABLAK_DURATION = data.get('GABLAK_DURATION', 5)
        engine.passed_players_r1 = set(data.get('passed_players_r1', []))
        engine.passed_players_r2 = set(data.get('passed_players_r2', []))
        engine.doubling_history = data.get('doubling_history', [])
        engine.has_bid_occurred = data.get('has_bid_occurred', False)

        # Phase handlers
        from .contract_handler import ContractHandler
        from .doubling_handler import DoublingHandler
        engine._contract = ContractHandler(engine)
        engine._doubling = DoublingHandler(engine)

        logger.info(f"BiddingEngine Restored from dict. Phase: {engine.phase}. Turn: {engine.current_turn}")
        return engine

    # ── Public API ───────────────────────────────────────────────────

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

    def is_bidding_complete(self):
        """Check if the main auction is finished (Contract secured or All Pass)."""
        return self.phase in [BiddingPhase.DOUBLING, BiddingPhase.VARIANT_SELECTION, BiddingPhase.FINISHED]

    def get_winner(self):
        """Return the winner of the bidding phase."""
        if self.contract.type:
             return {'player_index': self.contract.bidder_idx, 'contract': self.contract}
        return None

    # ── Bid Routing ──────────────────────────────────────────────────

    def process_bid(self, player_idx, action, suit=None, variant=None):
        logger.info(f"Process Bid: P{player_idx} wants {action} (Suit: {suit}, Phase: {self.phase.value})")

        # 0. Input validation
        if not isinstance(player_idx, int) or player_idx < 0 or player_idx >= 4:
            return {"error": f"Invalid player index: {player_idx}"}
        if not isinstance(action, str) or not action:
            return {"error": "Invalid bid action"}

        # 1. State Verification
        if self.phase == BiddingPhase.FINISHED:
             return {"error": "Bidding is finished"}
        
        # [KAWESH INTERCEPT]
        if action == "KAWESH":
             return self._handle_kawesh(player_idx)
        
        # 2. Phase Delegation
        if self.phase in [BiddingPhase.ROUND_1, BiddingPhase.ROUND_2, BiddingPhase.GABLAK_WINDOW]:
             return self._contract.handle_bid(player_idx, action, suit)
        elif self.phase == BiddingPhase.DOUBLING:
             return self._doubling.handle_bid(player_idx, action)
        elif self.phase == BiddingPhase.VARIANT_SELECTION:
             return self._doubling.handle_variant(player_idx, action)
        else:
             return {"error": "Invalid internal state"}

    def _handle_kawesh(self, player_idx):
        """
        Handle Kawesh declaration.
        Rules:
        1. Hand must be ONLY 7, 8, 9 (Zero points). A, K, Q, J, 10 forbidden.
        2. Pre-Bid: Redeal, SAME Dealer.
        3. Post-Bid: Redeal, ROTATE Dealer (Dealer Rotation).
        """
        player = next((p for p in self.players if p.index == player_idx), None)
        if not player:
            return {"error": f"Player {player_idx} not found"}
        
        if not is_kawesh_hand(player.hand):
             return {"error": "Cannot call Kawesh with points (A, K, Q, J, 10) in hand"}
        
        if self.has_bid_occurred:
             logger.info(f"Post-Bid Kawesh by P{player_idx}. Dealer Rotates.")
             return {"success": True, "action": "REDEAL", "rotate_dealer": True}
        else:
             logger.info(f"Pre-Bid Kawesh by P{player_idx}. Dealer Retained.")
             return {"success": True, "action": "REDEAL", "rotate_dealer": False}

    # ── Backward-compat delegates (used by some callers) ─────────────

    def _finalize_tentative_bid(self):
        """Called when Gablak timer expires. Delegates to handler."""
        return self._contract.finalize_tentative()

    def _finalize_auction(self):
        """Backward compat: delegates to contract handler."""
        return self._contract._finalize_auction()

    def _get_priority(self, player_idx):
        return self._contract.get_priority(player_idx)
