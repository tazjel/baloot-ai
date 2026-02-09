"""
game_engine/logic/autopilot.py — Extracted Auto-Play & Timeout Handler
=======================================================================

Replaces the ~120-line Game.auto_play_card() method.
Separates bot decision logic, human timeout fallback, and Qayd
auto-triggers from the core game rules.

The Game class calls:
    AutoPilot.execute(game, player_index)

This module is allowed to import from ai_worker (the Game class is NOT).

Design:
  - Game detects timeout -> calls AutoPilot.execute()
  - AutoPilot fetches a decision from bot_agent
  - AutoPilot calls game.play_card() / game.handle_bid() etc.
  - Game returns ActionResult with events
  - The caller (socket handler) broadcasts based on events
"""

from __future__ import annotations
import time
import logging
from typing import TYPE_CHECKING, Dict, Any, Optional

from game_engine.core.models import ActionResult, EventType
from game_engine.models.constants import GamePhase

if TYPE_CHECKING:
    from game_engine.logic.game import Game

logger = logging.getLogger(__name__)


class AutoPilot:
    """
    Handles automatic card play for bots and timed-out humans.
    Isolated from the Game class to keep game rules pure.
    """

    @staticmethod
    def execute(game: Game, player_index: int) -> ActionResult:
        """
        Execute an automatic action for the given player.
        Called by Game.check_timeout() or bot_orchestrator.

        Returns ActionResult from the delegated game action.
        """
        try:
            player = game.players[player_index]
            if not player.hand:
                return ActionResult.fail("Hand empty")

            t0 = time.time()

            # ── Get AI Decision ──────────────────────────────────────
            try:
                from ai_worker.agent import bot_agent
                decision = bot_agent.get_decision(game.get_game_state(), player_index)
            except Exception as e:
                logger.error(f"AutoPilot: AI agent failed for {player.name}: {e}")
                decision = {'action': 'PLAY_CARD', 'cardIndex': 0}

            dt = time.time() - t0
            logger.info(f"AutoPilot decision for {player.name}: {dt:.4f}s")

            action = decision.get('action', 'PLAY_CARD')
            card_idx = decision.get('cardIndex', 0)

            # ── Safety: Block bots from triggering Qayd UI for humans ─
            if action in ('QAYD_TRIGGER', 'QAYD_ACCUSATION') and not player.is_bot:
                logger.warning(
                    f"AutoPilot: Ignoring '{action}' for human {player.name}. "
                    "Falling back to card play."
                )
                action = 'PLAY_CARD'
                card_idx = AutoPilot._find_valid_card(game, player_index)

            # ── Route Action ─────────────────────────────────────────
            if action == 'QAYD_TRIGGER':
                logger.info(f"AutoPilot: {player.name} triggering Qayd (Sherlock)")
                return game.handle_qayd_trigger(player_index)

            elif action == 'QAYD_ACCUSATION':
                reporter_pos = game.qayd_state.get('reporter')
                if player.position != reporter_pos:
                    return ActionResult.ok(action="WAIT", reason="Not reporter")
                payload = decision.get('accusation', {})
                if game.phase == GamePhase.CHALLENGE.value:
                    return game.process_accusation(player_index, payload)
                return game.handle_qayd_trigger(player_index)

            elif action == 'QAYD_CONFIRM':
                return game.handle_qayd_confirm()

            elif action == 'WAIT':
                reason = decision.get('reason', 'Waiting')
                # Phantom Qayd detection (loop breaker)
                if "Qayd Investigation" in reason and game.phase == GamePhase.PLAYING.value:
                    logger.warning("PHANTOM QAYD detected during AutoPilot. Force-clearing.")
                    game.handle_qayd_cancel()
                    return ActionResult.ok(action="PHANTOM_REPAIR")
                return ActionResult.ok(action="WAIT", message=reason)

            elif action == 'SAWA':
                logger.info(f"AutoPilot: {player.name} declaring Sawa (Grand Slam)")
                res = game.handle_sawa(player_index)
                if res.get('success'):
                    return ActionResult.ok(action="SAWA", **res)
                # Sawa failed (shouldn't happen if AI checked correctly) — fall through to play
                logger.warning(f"AutoPilot: Sawa rejected for {player.name}: {res.get('error')}")
                card_idx = AutoPilot._find_valid_card(game, player_index)
                return game.play_card(player_index, card_idx)

            elif action == 'AKKA':
                logger.info(f"AutoPilot: {player.name} declaring Akka")
                res = game.handle_akka(player_index)
                if res.get('success'):
                    return ActionResult.ok(action="AKKA", **res)
                # Akka failed — fall through to play
                card_idx = AutoPilot._find_valid_card(game, player_index)
                return game.play_card(player_index, card_idx)

            # ── Default: Play a card ─────────────────────────────────
            card_idx = AutoPilot._clamp_card_index(game, player_index, card_idx)
            logger.info(f"AutoPilot: {player.name} playing card index {card_idx}")
            return game.play_card(player_index, card_idx)

        except Exception as e:
            logger.error(f"AutoPilot.execute crashed: {e}")
            # Ultimate fallback: play first valid card
            return AutoPilot._emergency_play(game, player_index)

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _find_valid_card(game: Game, player_index: int) -> int:
        """Find the index of the first valid card in the player's hand."""
        player = game.players[player_index]
        for i, c in enumerate(player.hand):
            if game.trick_manager.is_valid_move(c, player.hand):
                return i
        return 0  # Fallback to first card

    @staticmethod
    def _clamp_card_index(game: Game, player_index: int, card_idx: int) -> int:
        """Ensure card_idx is in range and points to a valid card."""
        player = game.players[player_index]
        if card_idx < 0 or card_idx >= len(player.hand):
            card_idx = 0

        if not game.trick_manager.is_valid_move(player.hand[card_idx], player.hand):
            card_idx = AutoPilot._find_valid_card(game, player_index)

        return card_idx

    @staticmethod
    def _emergency_play(game: Game, player_index: int) -> ActionResult:
        """Last-resort card play when everything else fails."""
        try:
            player = game.players[player_index]
            for i, c in enumerate(player.hand):
                if game.trick_manager.is_valid_move(c, player.hand):
                    logger.info(f"AutoPilot emergency: {player.name} playing index {i}")
                    return game.play_card(player_index, i)
            return ActionResult.fail("AutoPilot: No valid cards")
        except Exception as e:
            return ActionResult.fail(f"AutoPilot emergency failed: {e}")
