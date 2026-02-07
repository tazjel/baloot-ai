"""
game_engine/core/models.py — Typed Result & Event Models
=========================================================

Replaces raw {'success': True, 'error': ...} dicts with strict Pydantic models.
Only the API/socket layer converts these to JSON dicts for the frontend.

Usage:
    from game_engine.core.models import ActionResult, GameEvent, EventType
"""

from __future__ import annotations
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════
#  EVENT TYPES — What happened as a result of an action
# ═══════════════════════════════════════════════════════════════════════

class EventType(str, Enum):
    """All discrete events the game engine can emit."""
    # Bidding
    BID_PLACED       = "BID_PLACED"
    BID_COMPLETE     = "BID_COMPLETE"
    ALL_PASS_REDEAL  = "ALL_PASS_REDEAL"

    # Playing
    CARD_PLAYED      = "CARD_PLAYED"
    TRICK_WON        = "TRICK_WON"
    ROUND_END        = "ROUND_END"
    MATCH_END        = "MATCH_END"

    # Projects
    PROJECT_DECLARED = "PROJECT_DECLARED"
    PROJECTS_RESOLVED = "PROJECTS_RESOLVED"

    # Akka
    AKKA_DECLARED    = "AKKA_DECLARED"
    AKKA_REJECTED    = "AKKA_REJECTED"

    # Sawa
    SAWA_CLAIMED     = "SAWA_CLAIMED"
    SAWA_ACCEPTED    = "SAWA_ACCEPTED"
    SAWA_REFUSED     = "SAWA_REFUSED"

    # Qayd
    QAYD_TRIGGERED   = "QAYD_TRIGGERED"
    QAYD_STEP        = "QAYD_STEP"
    QAYD_VERDICT     = "QAYD_VERDICT"
    QAYD_CANCELLED   = "QAYD_CANCELLED"
    QAYD_PENALTY     = "QAYD_PENALTY"

    # Doubling
    DOUBLED          = "DOUBLED"

    # Timer / System
    TIMER_EXPIRED    = "TIMER_EXPIRED"
    BLUNDER          = "BLUNDER"

    # Phase transitions
    PHASE_CHANGED    = "PHASE_CHANGED"


class GameEvent(BaseModel):
    """A single discrete event emitted by a game action."""
    type: EventType
    data: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
#  ACTION RESULT — Unified return type for all Game methods
# ═══════════════════════════════════════════════════════════════════════

class ActionResult(BaseModel):
    """
    Every public Game method returns this.

    The socket/API layer reads .events to decide what to broadcast,
    and calls .to_legacy_dict() for backward-compatible payloads.
    """
    success: bool = True
    error: Optional[str] = None
    code: Optional[str] = None            # Machine-readable error code
    events: List[GameEvent] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)

    # Convenience constructors
    @classmethod
    def ok(cls, events: Optional[List[GameEvent]] = None, **payload) -> ActionResult:
        return cls(success=True, events=events or [], payload=payload)

    @classmethod
    def fail(cls, error: str, code: Optional[str] = None, **payload) -> ActionResult:
        return cls(success=False, error=error, code=code, payload=payload)

    def add_event(self, event_type: EventType, **data) -> ActionResult:
        """Fluent helper to append an event."""
        self.events.append(GameEvent(type=event_type, data=data))
        return self

    # ── Legacy bridge ──────────────────────────────────────────────────
    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Convert to the old {'success': bool, 'error': str, ...} format.
        Used by socket_handler.py during migration.
        """
        d: Dict[str, Any] = {"success": self.success}
        if self.error:
            d["error"] = self.error
        if self.code:
            d["code"] = self.code
        d.update(self.payload)
        return d


# ═══════════════════════════════════════════════════════════════════════
#  CARD KEY — Universal card identity helper
# ═══════════════════════════════════════════════════════════════════════

def card_key(card) -> str:
    """
    Returns a consistent "rank+suit" string (e.g. "A♠") from ANY card format.
    Handles: Card objects, flat dicts, nested {card: ...} wrappers.

    This is the ONE canonical function used everywhere in the engine.
    Frontend mirrors this in gameLogic.ts -> cardKey().
    """
    if card is None:
        return ""
    if isinstance(card, dict):
        if 'card' in card:
            return card_key(card['card'])
        return f"{card.get('rank', '')}{card.get('suit', '')}"
    if hasattr(card, 'rank') and hasattr(card, 'suit'):
        return f"{card.rank}{card.suit}"
    return str(card)
