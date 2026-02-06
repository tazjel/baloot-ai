from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

# Use existing models where possible to avoid circular deps
# from game_engine.models.card import Card
# from game_engine.models.constants import GamePhase

class GamePhaseState(str, Enum):
    WAITING = "WAITING"
    BIDDING = "BIDDING"
    VARIANT_SELECTION = "VARIANT_SELECTION"
    DOUBLING = "DOUBLING"
    PLAYING = "PLAYING"
    CHALLENGE = "CHALLENGE"
    FINISHED = "FINISHED"
    GAMEOVER = "GAMEOVER"

class PlayerState(BaseModel):
    index: int
    id: str
    name: str
    position: str
    hand: List[Dict[str, Any]] = Field(default_factory=list) # List of Card dicts
    captured_cards: List[Dict[str, Any]] = Field(default_factory=list)
    action_text: str = ""
    team: str # 'us' or 'them'
    avatar: Optional[str] = None
    thoughts: List[str] = Field(default_factory=list)

class TrickState(BaseModel):
    cards: List[Dict[str, Any]] = Field(default_factory=list) # {card, playedBy, playerId}
    winner: Optional[str] = None # Position
    points: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BidState(BaseModel):
    type: Optional[str] = None
    bidder: Optional[str] = None # Position
    doubled: bool = False
    suit: Optional[str] = None
    level: int = 1
    variant: Optional[str] = None
    isAshkal: bool = False
    isTentative: bool = False

class GameState(BaseModel):
    roomId: str
    phase: GamePhaseState = GamePhaseState.WAITING
    
    # Core Counters
    currentTurnIndex: int = 0
    dealerIndex: int = 0
    biddingRound: int = 1
    
    # Scores
    teamScores: Dict[str, int] = {"us": 0, "them": 0}
    matchScores: Dict[str, int] = {"us": 0, "them": 0}
    
    # State Objects
    players: List[PlayerState] = Field(default_factory=list)
    tableCards: List[Dict[str, Any]] = Field(default_factory=list)
    floorCard: Optional[Dict[str, Any]] = None # Card dict
    
    # Game Settings (Context)
    gameMode: Optional[str] = None # 'SUN' or 'HOKUM'
    trumpSuit: Optional[str] = None
    bid: BidState = Field(default_factory=BidState)
    doublingLevel: int = 1
    isLocked: bool = False
    
    # History
    roundHistory: List[TrickState] = Field(default_factory=list) # Current Round
    pastRoundResults: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Sub-System States (Opaque dicts for flexibility initially)
    qaydState: Dict[str, Any] = Field(default_factory=dict)
    sawaState: Dict[str, Any] = Field(default_factory=dict)
    akkaState: Optional[Dict[str, Any]] = None
    declarations: Dict[str, Any] = Field(default_factory=dict)
    
    # Meta
    isProjectRevealing: bool = False
    dealingPhase: int = 0 # 0, 1, 2, 3
    timer: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True
