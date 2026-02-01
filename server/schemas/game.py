from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any, Union
from server.schemas.base import GamePhase, BiddingPhase, BidType, Team
from server.schemas.cards import CardModel

class PlayerModel(BaseModel):
    id: str
    name: str
    avatar: str
    index: int
    hand: List[CardModel] = []
    score: int = 0
    team: Team
    position: str
    isDealer: bool
    actionText: str = ""
    lastReasoning: str = ""
    isBot: bool
    isActive: bool = False
    isThinking: bool = False

class TableCardModel(BaseModel):
    playerId: str
    card: CardModel
    playedBy: str
    metadata: Optional[Dict[str, Any]] = None

class TimerState(BaseModel):
    remaining: float
    duration: float
    elapsed: float
    active: bool

class AnalyticsModel(BaseModel):
    winProbability: List[float] = []
    blunders: List[Any] = []

class GameStateModel(BaseModel):
    roomId: str
    phase: GamePhase
    biddingPhase: Optional[str] = None # String because sometimes it's None or Enum name
    players: List[PlayerModel]
    tableCards: List[TableCardModel]
    currentTurnIndex: int
    gameMode: Optional[str] = None
    trumpSuit: Optional[str] = None
    bid: Optional[Dict[str, Any]] = None
    teamScores: Dict[str, int]
    matchScores: Dict[str, int]
    analytics: AnalyticsModel
    floorCard: Optional[CardModel] = None
    dealerIndex: int
    biddingRound: int
    declarations: Dict[str, List[Dict[str, Any]]] # Complex structure, kept generic for now
    timer: TimerState
    isProjectRevealing: bool
    doublingLevel: int
    isLocked: bool
    dealingPhase: str
    lastTrick: Optional[Any] = None
    roundHistory: List[Any] = []
    currentRoundTricks: List[Any] = []
    sawaState: Optional[Dict[str, Any]] = None
    qaydState: Optional[Dict[str, Any]] = None
    challengeActive: bool
    timerStartTime: float
    turnDuration: float
    serverTime: float
    akkaState: Optional[Dict[str, Any]] = None
    gameId: str
    settings: Dict[str, Any] = {}

    model_config = ConfigDict(populate_by_name=True)
