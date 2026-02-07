"""
game_engine/logic/phases/base.py — Phase Handler Pattern
=========================================================

Abstract base class for game phase handlers.
Each phase implements:
  - handle_action(game, player_index, action, payload) -> ActionResult
  - on_timeout(game) -> ActionResult

The Game class delegates all actions and timeouts:
    return self.phases[self.state.phase].handle_action(...)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any, Optional

from game_engine.core.models import ActionResult

if TYPE_CHECKING:
    from game_engine.logic.game import Game


class PhaseHandler(ABC):
    """Abstract base class for all game phase handlers."""

    def __init__(self, game: Game):
        self.game = game

    @abstractmethod
    def handle_action(
        self,
        player_index: int,
        action: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> ActionResult:
        """Process a player action during this phase."""
        ...

    @abstractmethod
    def on_timeout(self) -> ActionResult:
        """Handle timer expiry during this phase."""
        ...

    def on_enter(self):
        """Called when the game transitions INTO this phase."""
        pass

    def on_exit(self):
        """Called when the game transitions OUT OF this phase."""
        pass
