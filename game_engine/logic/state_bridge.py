"""
game_engine/logic/state_bridge.py — Legacy Property Bridge
============================================================

Mixin class that provides property aliases from Game to GameState.
These allow existing code (managers, socket_handler, phases) to continue
using game.phase, game.bid, etc. while the actual data lives in game.state.

As callers are migrated to use game.state.X directly, these properties
can be removed one by one.
"""

from __future__ import annotations
import logging
from typing import Dict
from game_engine.core.state import GamePhaseState, BidState, SawaState, AkkaState
from game_engine.models.constants import GamePhase

logger = logging.getLogger(__name__)


class StateBridgeMixin:
    """
    Mixin providing property aliases: game.X <-> game.state.X.
    Inherit this BEFORE defining the Game class body.
    """

    # ── Phase ─────────────────────────────────────────────────────────

    @property
    def room_id(self) -> str:
        return self.state.roomId

    @property
    def phase(self) -> str:
        v = self.state.phase
        return v.value if isinstance(v, GamePhaseState) else v

    @phase.setter
    def phase(self, value: str):
        try:
            self.state.phase = GamePhaseState(value)
        except ValueError:
            logger.warning(f"Invalid phase: {value}")

    @property
    def dealer_index(self) -> int:
        return self.state.dealerIndex

    @dealer_index.setter
    def dealer_index(self, v: int):
        self.state.dealerIndex = v

    @property
    def current_turn(self) -> int:
        if self.phase == GamePhase.BIDDING.value and hasattr(self, 'bidding_engine') and self.bidding_engine:
            return self.bidding_engine.get_current_actor()
        return self.state.currentTurnIndex

    @current_turn.setter
    def current_turn(self, v: int):
        self.state.currentTurnIndex = v

    # ── Mode / Bid ────────────────────────────────────────────────────

    @property
    def game_mode(self):
        return self.state.gameMode

    @game_mode.setter
    def game_mode(self, v):
        self.state.gameMode = v

    @property
    def trump_suit(self):
        return self.state.trumpSuit

    @trump_suit.setter
    def trump_suit(self, v):
        self.state.trumpSuit = v

    @property
    def bid(self) -> Dict:
        b = self.state.bid
        return {
            "type": b.type, "bidder": b.bidder, "doubled": b.doubled,
            "suit": b.suit, "level": b.level, "variant": b.variant,
            "isAshkal": b.isAshkal, "isTentative": b.isTentative,
        }

    @bid.setter
    def bid(self, v: Dict):
        if isinstance(v, dict):
            self.state.bid = BidState(**{k: v.get(k) for k in BidState.model_fields if k in v})

    @property
    def doubling_level(self):
        return self.state.doublingLevel

    @doubling_level.setter
    def doubling_level(self, v):
        self.state.doublingLevel = v

    @property
    def is_locked(self):
        return self.state.isLocked

    @is_locked.setter
    def is_locked(self, v):
        self.state.isLocked = v

    @property
    def strictMode(self):
        return self.state.strictMode

    @strictMode.setter
    def strictMode(self, v):
        self.state.strictMode = v

    # ── Scores ────────────────────────────────────────────────────────

    @property
    def team_scores(self):
        return self.state.teamScores

    @team_scores.setter
    def team_scores(self, v):
        self.state.teamScores = v

    @property
    def match_scores(self):
        return self.state.matchScores

    @match_scores.setter
    def match_scores(self, v):
        self.state.matchScores = v

    # ── History ───────────────────────────────────────────────────────

    @property
    def round_history(self):
        return self.state.roundHistory

    @round_history.setter
    def round_history(self, v):
        self.state.roundHistory = v

    @property
    def trick_history(self):
        return self.state.trickHistory

    @trick_history.setter
    def trick_history(self, v):
        self.state.trickHistory = v

    @property
    def past_round_results(self):
        return self.state.pastRoundResults

    @past_round_results.setter
    def past_round_results(self, v):
        self.state.pastRoundResults = v

    @property
    def full_match_history(self):
        return self.state.fullMatchHistory

    @full_match_history.setter
    def full_match_history(self, v):
        self.state.fullMatchHistory = v

    @property
    def last_trick(self):
        return self.state.lastTrick

    @last_trick.setter
    def last_trick(self, v):
        self.state.lastTrick = v

    # ── Declarations & Hands ─────────────────────────────────────────

    @property
    def declarations(self):
        return self.state.declarations

    @declarations.setter
    def declarations(self, v):
        self.state.declarations = v

    @property
    def trick_1_declarations(self):
        return self.state.trick1Declarations

    @trick_1_declarations.setter
    def trick_1_declarations(self, v):
        self.state.trick1Declarations = v

    @property
    def initial_hands(self):
        return self.state.initialHands

    @initial_hands.setter
    def initial_hands(self, v):
        self.state.initialHands = v

    # ── Presentation Flags ───────────────────────────────────────────

    @property
    def is_project_revealing(self):
        return self.state.isProjectRevealing

    @is_project_revealing.setter
    def is_project_revealing(self, v):
        self.state.isProjectRevealing = v

    @property
    def dealing_phase(self):
        return self.state.dealingPhase

    @dealing_phase.setter
    def dealing_phase(self, v):
        self.state.dealingPhase = v

    # ── Floor Card (special: object <-> dict) ──────────────────────────

    @property
    def floor_card(self):
        return self._floor_card_obj

    @floor_card.setter
    def floor_card(self, v):
        self._floor_card_obj = v
        self.state.floorCard = v.to_dict() if v and hasattr(v, 'to_dict') else v

    # ── Analytics ─────────────────────────────────────────────────────

    @property
    def win_probability_history(self):
        return self.state.winProbabilityHistory

    @win_probability_history.setter
    def win_probability_history(self, v):
        self.state.winProbabilityHistory = v

    @property
    def blunders(self):
        return self.state.blunders

    @blunders.setter
    def blunders(self, v):
        self.state.blunders = v

    @property
    def metadata(self):
        return self.state.metadata

    @metadata.setter
    def metadata(self, v):
        self.state.metadata = v

    # ── Sawa ──────────────────────────────────────────────────────────

    @property
    def sawa_state(self):
        s = self.state.sawaState
        return {"active": s.active, "claimer": s.claimer, "responses": s.responses, "status": s.status, "challenge_active": s.challenge_active}

    @sawa_state.setter
    def sawa_state(self, v):
        if isinstance(v, dict):
            self.state.sawaState = SawaState(**{k: v.get(k) for k in SawaState.model_fields if k in v})

    @property
    def sawa_failed_khasara(self):
        return self.state.sawaFailedKhasara

    @sawa_failed_khasara.setter
    def sawa_failed_khasara(self, v):
        self.state.sawaFailedKhasara = v

    # ── Akka ──────────────────────────────────────────────────────────

    @property
    def akka_state(self):
        a = self.state.akkaState
        if not a or not a.active:
            return None
        return {'active': a.active, 'claimer': a.claimer, 'claimerIndex': a.claimerIndex, 'suits': a.suits, 'timestamp': a.timestamp}

    @akka_state.setter
    def akka_state(self, v):
        if v is None:
            self.state.akkaState = AkkaState()
        elif isinstance(v, dict):
            self.state.akkaState = AkkaState(**{k: v.get(k) for k in AkkaState.model_fields if k in v})
