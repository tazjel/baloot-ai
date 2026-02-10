"""
game_engine/core/state.py — Single Source of Truth
===================================================

Replaces:
  - All shadow attributes on Game.__init__ (self.bid, self.game_mode, etc.)
  - The manual _sync_state_from_legacy() bridge
  - Pickle serialization with JSON-native Pydantic serialization

The Game class accesses self.state.X directly for ALL mutable state.
Persistence becomes: redis.set(key, game.state.model_dump_json())

Migration note:
  Property aliases on Game (e.g. game.phase -> game.state.phase) are kept
  for backward compatibility during the transition, but all NEW code should
  access game.state directly.
"""

from __future__ import annotations
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════
#  ENUMS
# ═══════════════════════════════════════════════════════════════════════

class GamePhaseState(str, Enum):
    WAITING            = "WAITING"
    BIDDING            = "BIDDING"
    VARIANT_SELECTION  = "VARIANT_SELECTION"
    DOUBLING           = "DOUBLING"
    PLAYING            = "PLAYING"
    CHALLENGE          = "CHALLENGE"
    FINISHED           = "FINISHED"
    GAMEOVER           = "GAMEOVER"


# ═══════════════════════════════════════════════════════════════════════
#  SUB-MODELS
# ═══════════════════════════════════════════════════════════════════════

class CardDict(BaseModel):
    """Serializable card representation used in state."""
    suit: str
    rank: str
    id: Optional[str] = None
    value: int = 0

    model_config = ConfigDict(extra="allow")


class PlayerState(BaseModel):
    index: int
    id: str
    name: str
    position: str
    hand: List[Dict[str, Any]] = Field(default_factory=list)
    captured_cards: List[Dict[str, Any]] = Field(default_factory=list)
    action_text: str = ""
    team: str  # 'us' or 'them'
    avatar: Optional[str] = None
    is_bot: bool = False
    thoughts: List[str] = Field(default_factory=list)
    strategy: str = "heuristic"
    profile: Optional[str] = None


class BidState(BaseModel):
    type: Optional[str] = None        # 'SUN' | 'HOKUM' | None
    bidder: Optional[str] = None      # Position string
    doubled: bool = False
    suit: Optional[str] = None        # Trump suit symbol
    level: int = 1
    variant: Optional[str] = None     # 'OPEN' | 'CLOSED'
    isAshkal: bool = False
    isTentative: bool = False


class TrickState(BaseModel):
    cards: List[Dict[str, Any]] = Field(default_factory=list)
    winner: Optional[str] = None
    points: int = 0
    playedBy: List[str] = Field(default_factory=list)
    metadata: List[Optional[Dict[str, Any]]] = Field(default_factory=list)


class TimerState(BaseModel):
    remaining: float = 0.0
    duration: float = 30.0
    elapsed: float = 0.0
    active: bool = False


class SawaState(BaseModel):
    active: bool = False
    claimer: Optional[str] = None
    responses: Dict[str, str] = Field(default_factory=dict)
    status: str = "NONE"  # NONE | PENDING | ACCEPTED | REFUSED
    challenge_active: bool = False


class AkkaState(BaseModel):
    active: bool = False
    claimer: Optional[str] = None
    claimerIndex: Optional[int] = None
    suits: List[str] = Field(default_factory=list)
    timestamp: float = 0.0


# ═══════════════════════════════════════════════════════════════════════
#  GAME STATE — Complete, serializable snapshot
# ═══════════════════════════════════════════════════════════════════════

class GameState(BaseModel):
    """
    The ONE canonical data store for a Baloot game.

    Rules:
      - Game class reads/writes self.state.fieldName
      - No shadow attributes (self.bid, self.game_mode) on Game
      - Persistence: redis.set(key, state.model_dump_json())
      - Deserialization: GameState.model_validate_json(data)
    """
    roomId: str

    # Phase & Turn
    phase: GamePhaseState = GamePhaseState.WAITING
    currentTurnIndex: int = 0
    dealerIndex: int = 0

    # Bid & Mode
    bid: BidState = Field(default_factory=BidState)
    gameMode: Optional[str] = None       # 'SUN' | 'HOKUM'
    trumpSuit: Optional[str] = None      # Suit symbol
    biddingRound: int = 1
    doublingLevel: int = 1
    isLocked: bool = False
    strictMode: bool = False

    # Scores
    teamScores: Dict[str, int] = Field(default_factory=lambda: {"us": 0, "them": 0})
    matchScores: Dict[str, int] = Field(default_factory=lambda: {"us": 0, "them": 0})

    # Players
    players: List[PlayerState] = Field(default_factory=list)

    # Table & Tricks
    tableCards: List[Dict[str, Any]] = Field(default_factory=list)
    floorCard: Optional[Dict[str, Any]] = None
    roundHistory: List[Dict[str, Any]] = Field(default_factory=list)     # Tricks this round
    trickHistory: List[Dict[str, Any]] = Field(default_factory=list)     # All tricks this match
    pastRoundResults: List[Dict[str, Any]] = Field(default_factory=list)
    fullMatchHistory: List[Dict[str, Any]] = Field(default_factory=list)
    lastTrick: Optional[Dict[str, Any]] = None

    # Initial hands (for replay)
    initialHands: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)

    # Graveyard (played cards tracking — populated from Graveyard object)
    graveyardSeen: List[str] = Field(default_factory=list)

    # Sub-system states
    sawaState: SawaState = Field(default_factory=SawaState)
    sawaFailedKhasara: bool = False
    resolved_crimes: List[str] = Field(default_factory=list) # Ledger of processed violations
    akkaState: AkkaState = Field(default_factory=AkkaState)
    qaydState: Dict[str, Any] = Field(default_factory=dict)
    declarations: Dict[str, Any] = Field(default_factory=dict)
    trick1Declarations: Dict[str, Any] = Field(default_factory=dict)

    # Presentation flags
    isProjectRevealing: bool = False
    dealingPhase: int = 0

    # Analytics
    winProbabilityHistory: List[Dict[str, Any]] = Field(default_factory=list)
    blunders: Dict[str, int] = Field(default_factory=dict)

    # Timer (snapshot for frontend)
    timer: TimerState = Field(default_factory=TimerState)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ── Convenience ────────────────────────────────────────────────────

    def reset_round(self):
        """Reset all round-level fields. Called at start of new round."""
        self.tableCards = []
        self.bid = BidState()
        self.gameMode = None
        self.trumpSuit = None
        self.floorCard = None
        self.biddingRound = 1
        self.doublingLevel = 1
        self.isLocked = False
        self.dealingPhase = 0
        self.roundHistory = []
        self.lastTrick = None
        self.isProjectRevealing = False
        self.declarations = {}
        self.trick1Declarations = {}
        self.initialHands = {}
        self.sawaState = SawaState()
        self.sawaFailedKhasara = False
        self.akkaState = AkkaState()
        self.graveyardSeen = []
        self.resolved_crimes.clear()  # Reset Qayd ledger — trick indices restart at 0 each round
