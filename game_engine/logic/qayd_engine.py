"""
QaydEngine — Unified Forensic Challenge System (Refactored)
============================================================

STATE MACHINE ONLY - All validation delegated to RulesValidator
NO BOT LOGIC - Bot detection moved to ForensicScanner in ai_worker

Replaces:
  - qayd_manager.py (no longer used)
  - challenge_phase.py Qayd methods (extracted)
  - trick_manager.py propose_qayd/confirm_qayd/cancel_qayd (extracted)

State Machine:
  IDLE → MAIN_MENU → VIOLATION_SELECT → SELECT_CARD_1 → SELECT_CARD_2 → ADJUDICATION → RESULT → IDLE

Single source of truth for all Qayd state. Game.qayd_state is an alias
to QaydEngine.state (same dict object, never reassigned).

MISSION 2 & 3 REFACTORING:
- Removed _bot_auto_accuse (now in ForensicScanner)
- Removed _validate_* methods (now in RulesValidator)
- Removed handle_legacy_accusation (bots use proper API now)
- Clean separation: Engine = State, Validator = Rules, Scanner = Detection

MISSION 6 REFACTORING:
- Extracted state machine to game_engine/logic/qayd_state_machine.py
- Extracted penalty logic to game_engine/logic/qayd_penalties.py
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple

from game_engine.models.constants import GamePhase
from game_engine.logic.rules_validator import RulesValidator, ViolationType
from game_engine.logic.qayd_state_machine import QaydStateMachine, QaydStep, QaydMenuOption, TIMER_HUMAN, TIMER_AI
from game_engine.logic.qayd_penalties import QaydPenaltyCalculator

logger = logging.getLogger(__name__)


# ─── Step Constants (Re-exported for compatibility) ───────────────────────────
# QaydStep and QaydMenuOption are imported from qayd_state_machine.py

class QaydEngine:
    """
    Unified Qayd (Forensic Challenge) Engine - Refactored.

    Usage:
        engine = QaydEngine(game)
        game.qayd_state = engine.state   # alias — NEVER reassign game.qayd_state

    All mutations go through engine methods. The dict is mutated IN-PLACE
    so all aliases remain valid.
    
    REFACTORING NOTES:
    - Bot auto-accusation logic moved to ai_worker/strategies/components/forensics.py
    - Validation logic moved to game_engine/logic/rules_validator.py
    - State machine logic moved to game_engine/logic/qayd_state_machine.py
    - Penalty logic moved to game_engine/logic/qayd_penalties.py
    """

    def __init__(self, game):
        self.game = game
        self._sm = QaydStateMachine()
        self.state = self._sm.state  # Alias to the state dict inside state machine
        # Note: ignored_crimes moved to ForensicScanner (bot-specific)

    # ══════════════════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════

    def trigger(self, player_index: int) -> Dict[str, Any]:
        """
        Step 0 → Step 1 (MAIN_MENU).
        Called when a player presses the Qayd button.
        Locks the game and pauses timers.
        
        NOTE: Bot detection is now handled externally by ForensicScanner.
        Bots should call this, then immediately call accusation methods.
        """
        if self.state['active']:
            return {'success': False, 'error': 'Qayd already active'}

        if self.game.is_locked:
            return {'success': False, 'error': 'Game is locked'}

        phase_str = str(self.game.phase)
        if phase_str in (GamePhase.FINISHED.value, GamePhase.GAMEOVER.value, 'FINISHED', 'GAMEOVER'):
            logger.warning(f"[QAYD] Trigger rejected — phase is {self.game.phase}")
            return {'success': False, 'error': f'Cannot trigger Qayd in {self.game.phase}'}

        player = self.game.players[player_index]

        self.game.is_locked = True
        self.game.phase = GamePhase.CHALLENGE.value
        self.game.pause_timer()  # Properly pause TimerManager so auto-play doesn't fire

        is_bot = getattr(player, 'is_bot', False)
        
        # Delegate state transition
        timer_dur = self._sm.start_session(player.position, is_bot)

        logger.info(f"[QAYD] Triggered by {player.position} (bot={is_bot}). Timer={timer_dur}s. Phase → CHALLENGE.")

        return {'success': True, 'qayd_state': self.state}

    def select_menu_option(self, option: str) -> Dict[str, Any]:
        """Step 1 (MAIN_MENU) → Step 2 (VIOLATION_SELECT)."""
        if self.state['step'] != QaydStep.MAIN_MENU:
            return {'success': False, 'error': f"Wrong step: {self.state['step']}"}

        self._sm.to_violation_select(option)
        return {'success': True, 'qayd_state': self.state}

    def select_violation(self, violation_type: str) -> Dict[str, Any]:
        """Step 2 (VIOLATION_SELECT) → Step 3 (SELECT_CARD_1). Also allows re-selection from SELECT_CARD_1/2."""
        if self.state['step'] not in (QaydStep.VIOLATION_SELECT, QaydStep.SELECT_CARD_1, QaydStep.SELECT_CARD_2):
            return {'success': False, 'error': f"Wrong step: {self.state['step']}"}

        self._sm.to_card_select_1(violation_type)
        return {'success': True, 'qayd_state': self.state}

    def select_crime_card(self, card_data: Dict) -> Dict[str, Any]:
        """Step 3 (SELECT_CARD_1) → Step 4 (SELECT_CARD_2). Also allows re-selection from SELECT_CARD_2."""
        logger.info(f"[QAYD] select_crime_card called. step={self.state['step']}, card_data={card_data}")
        if self.state['step'] not in (QaydStep.SELECT_CARD_1, QaydStep.SELECT_CARD_2):
            logger.warning(f"[QAYD] select_crime_card REJECTED: wrong step {self.state['step']}")
            return {'success': False, 'error': f"Wrong step: {self.state['step']}"}

        if not self._validate_card_in_history(card_data):
            logger.warning(f"[QAYD] select_crime_card REJECTED: card not in history. card_data={card_data}")
            return {'success': False, 'error': 'Card not found in round history'}

        # --- LEDGER CHECK (Prevent Double Jeopardy) ---
        trick_idx = card_data.get('trick_idx')
        card_idx = card_data.get('card_idx')
        if trick_idx is not None and card_idx is not None:
            ledger_sig = f"{trick_idx}_{card_idx}"
            if ledger_sig in self.game.state.resolved_crimes:
                logger.warning(f"[QAYD] Selection blocked: Crime {ledger_sig} already resolved.")
                return {'success': False, 'error': 'This play has already been challenged.'}

        self._sm.to_card_select_2(card_data)
        logger.info(f"[QAYD] select_crime_card SUCCESS → step=SELECT_CARD_2")
        return {'success': True, 'qayd_state': self.state}

    def select_proof_card(self, card_data: Dict) -> Dict[str, Any]:
        """Step 4 (SELECT_CARD_2) → ADJUDICATION → RESULT."""
        logger.info(f"[QAYD] select_proof_card called. step={self.state['step']}, card_data={card_data}")
        if self.state['step'] != QaydStep.SELECT_CARD_2:
            logger.warning(f"[QAYD] select_proof_card REJECTED: wrong step {self.state['step']}")
            return {'success': False, 'error': f"Wrong step: {self.state['step']}"}

        if not self._validate_card_in_history(card_data):
            logger.warning(f"[QAYD] select_proof_card REJECTED: card not in history. card_data={card_data}")
            return {'success': False, 'error': 'Proof card not found in round history'}

        self._sm.to_adjudication(card_data)
        logger.info(f"[QAYD] select_proof_card → calling _adjudicate()")
        return self._adjudicate()

    def confirm(self) -> Dict[str, Any]:
        """
        Step 6 (RESULT) → Apply penalty and end round.
        Called when frontend sends QAYD_CONFIRM after viewing verdict.
        """
        if self.state['step'] not in (QaydStep.RESULT, QaydStep.ADJUDICATION):
            if not self.state['active']:
                return {'success': False, 'error': 'No active Qayd to confirm'}
            return {'success': False, 'error': f"Cannot confirm in step {self.state['step']}"}

        loser_team = self.state['loser_team']
        penalty = self.state['penalty_points']

        if not loser_team:
            logger.error("[QAYD] confirm() called but loser_team is None")
            self._unlock_and_reset()
            return {'success': False, 'error': 'Internal: no loser_team'}

        winner_team = 'us' if loser_team == 'them' else 'them'

        logger.info(f"[QAYD] CONFIRMED: {self.state['verdict']}. {loser_team} penalized {penalty} pts → {winner_team}")

        # Add crime to ledger (persistent)
        sig = self.state.get('crime_signature')
        if sig:
            ledger_sig = f"{sig[0]}_{sig[1]}"
            if ledger_sig not in self.game.state.resolved_crimes:
                self.game.state.resolved_crimes.append(ledger_sig)
                logger.info(f"[LEDGER] Crime {ledger_sig} added to permanent history.")

        # Apply penalty through game (ends the round)
        self.game.apply_qayd_penalty(loser_team, winner_team)

        # Mark resolved
        self._sm.resolve()

        self.game.is_locked = False
        self.game.resume_timer()

        return {
            'success': True,
            'verdict': self.state.get('verdict'),
            'loser_team': loser_team,
            'penalty_points': penalty,
            'trigger_next_round': True,
        }

    def cancel(self) -> Dict[str, Any]:
        """Cancel/close the Qayd at any step. Resumes normal gameplay."""
        if not self.state['active']:
            return {'success': False, 'error': 'No active Qayd'}

        was_result = self.state['step'] == QaydStep.RESULT
        self._sm.reset()

        # Restore phase
        if not was_result:
            phase_str = str(self.game.phase)
            if phase_str in (GamePhase.CHALLENGE.value, 'CHALLENGE'):
                self.game.phase = GamePhase.PLAYING.value
                logger.info("[QAYD] Phase reset CHALLENGE → PLAYING.")

        self.game.is_locked = False
        self.game.resume_timer()

        return {'success': True}

    def reset(self):
        """Full reset for new round. Called by game.reset_round_state()."""
        self._sm.reset()
        # Note: ForensicScanner handles its own session reset

    def check_timeout(self) -> Optional[Dict[str, Any]]:
        """Called by game's background timer loop."""
        if not self.state['active']:
            return None

        elapsed = time.time() - self.state['timer_start']
        if elapsed < self.state['timer_duration']:
            return None

        logger.info(f"[QAYD] Timer expired ({elapsed:.1f}s / {self.state['timer_duration']}s)")

        if self.state['step'] == QaydStep.RESULT:
            return self.confirm()

        logger.info("[QAYD] Selection timeout — cancelling.")
        return self.cancel()

    # ══════════════════════════════════════════════════════════════════════════
    #  ADJUDICATION (Delegates to RulesValidator)
    # ══════════════════════════════════════════════════════════════════════════

    def _adjudicate(self) -> Dict[str, Any]:
        """
        Validate the accusation after both cards selected.
        
        REFACTORED: Now delegates to RulesValidator instead of inline logic.
        """
        crime = self.state['crime_card']
        proof = self.state['proof_card']
        violation = self.state['violation_type']
        reporter_pos = self.state['reporter']
        
        reporter = next((p for p in self.game.players if p.position == reporter_pos), None)

        if not crime or not reporter:
            self._unlock_and_reset()
            return {'success': False, 'error': 'Missing crime card or reporter'}

        offender_pos = crime.get('played_by')
        offender = next((p for p in self.game.players if p.position == offender_pos), None)

        # Build game context for validator
        game_context = {
            'trump_suit': self.game.trump_suit,
            'game_mode': str(self.game.game_mode or '').upper(),
            'round_history': self.game.round_history,
            'table_cards': self.game.table_cards,
            'players': self.game.players,
        }

        # DELEGATION: Call RulesValidator
        is_guilty, reason = RulesValidator.validate(
            violation_type=violation,
            crime=crime,
            proof=proof,
            game_context=game_context
        )

        # Build verdict
        if is_guilty:
            verdict = 'CORRECT'
            verdict_msg = 'قيد صحيح'
            loser_team = offender.team if offender else reporter.team
        else:
            verdict = 'WRONG'
            verdict_msg = 'قيد خاطئ'
            loser_team = reporter.team

        # Use new PenaltyCalculator
        penalty = QaydPenaltyCalculator.calculate_base_penalty(
            self.game.game_mode, 
            getattr(self.game, 'doubling_level', 1)
        )
        
        sig = (crime.get('trick_idx', -1), crime.get('card_idx', -1))

        self._sm.to_result(
            verdict=verdict,
            verdict_msg=verdict_msg,
            loser_team=loser_team,
            penalty=penalty,
            reason=reason,
            sig=sig,
            target_play={
                'card': crime,
                'playedBy': offender_pos,
                'metadata': {'illegal_reason': reason},
            }
        )

        logger.info(f"[QAYD] Adjudicated: {verdict} — {reason}. Penalty={penalty}")
        return {'success': True, 'qayd_state': self.state}

    # ══════════════════════════════════════════════════════════════════════════
    #  HELPER METHODS (Non-validation)
    # ══════════════════════════════════════════════════════════════════════════

    def _validate_card_in_history(self, card_data: Dict) -> bool:
        """Check that a card reference points to a real card (History, Table, or Hand)."""
        trick_idx = card_data.get('trick_idx', -1)
        card_idx = card_data.get('card_idx', -1)
        player_pos = card_data.get('played_by')
        
        history_len = len(self.game.round_history)
        table_len = len(self.game.table_cards)
        logger.debug(f"[QAYD] _validate_card_in_history: trick_idx={trick_idx}, card_idx={card_idx}, "
                    f"played_by={player_pos}, history_len={history_len}, table_len={table_len}")

        # Case 1: Card in Hand (trick_idx == -1)
        if trick_idx == -1:
            if not player_pos:
                logger.warning(f"[QAYD] Validation FAIL: trick_idx=-1 but no player_pos")
                return False
            player = next((p for p in self.game.players if p.position == player_pos), None)
            if not player or not player.hand:
                logger.warning(f"[QAYD] Validation FAIL: player {player_pos} not found or empty hand")
                return False
            result = 0 <= card_idx < len(player.hand)
            logger.debug(f"[QAYD] Validation (hand): card_idx={card_idx}, hand_len={len(player.hand)}, result={result}")
            return result

        # Case 2: Card currently on Table
        if trick_idx == history_len:
            result = 0 <= card_idx < table_len
            logger.debug(f"[QAYD] Validation (table): card_idx={card_idx}, table_len={table_len}, result={result}")
            return result

        # Case 3: Card in confirmed History
        if 0 <= trick_idx < history_len:
            trick = self.game.round_history[trick_idx]
            cards = trick.get('cards', [])
            if 0 <= card_idx < len(cards):
                logger.debug(f"[QAYD] Validation (history cards): OK. trick_idx={trick_idx}, card_idx={card_idx}")
                return True
            played_by = trick.get('playedBy', [])
            if 0 <= card_idx < len(played_by):
                logger.debug(f"[QAYD] Validation (history playedBy): OK. trick_idx={trick_idx}, card_idx={card_idx}")
                return True
            logger.warning(f"[QAYD] Validation FAIL: trick_idx={trick_idx} in range but card_idx={card_idx} out of bounds. "
                          f"cards_len={len(cards)}, playedBy_len={len(played_by)}")
            return False

        logger.warning(f"[QAYD] Validation FAIL: trick_idx={trick_idx} out of range [0, {history_len})")
        return False

    def _calculate_penalty(self) -> int:
        """
        DEPRECATED: Use QaydPenaltyCalculator instead.
        Kept for safe measure if needed internally.
        """
        return QaydPenaltyCalculator.calculate_base_penalty(
            self.game.game_mode, 
            getattr(self.game, 'doubling_level', 1)
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _update(self, patch: Dict[str, Any]):
        """In-place update. Never reassign self.state."""
        self._sm.update(patch)

    def _reset_state(self):
        """Reset to idle. Preserves dict identity."""
        self._sm.reset()

    def _unlock_and_reset(self):
        """Reset state AND unlock game + restore phase."""
        self._sm.reset()
        self.game.is_locked = False
        self.game.resume_timer()
        phase_str = str(self.game.phase)
        if phase_str in (GamePhase.CHALLENGE.value, 'CHALLENGE'):
            self.game.phase = GamePhase.PLAYING.value

    def get_frontend_state(self) -> Dict[str, Any]:
        """Serializable view for get_game_state()."""
        if not self.state['active']:
            return {'active': False}

        return {
            'active':           self.state['active'],
            'step':             self.state['step'],
            'reporter':         self.state['reporter'],
            'reporter_is_bot':  self.state['reporter_is_bot'],
            'menu_option':      self.state['menu_option'],
            'violation_type':   self.state['violation_type'],
            'crime_card':       self.state['crime_card'],
            'proof_card':       self.state['proof_card'],
            'verdict':          self.state['verdict'],
            'verdict_message':  self.state['verdict_message'],
            'loser_team':       self.state['loser_team'],
            'penalty_points':   self.state['penalty_points'],
            'timer_duration':   self.state['timer_duration'],
            'timer_start':      self.state['timer_start'],
            'status':           self.state['status'],
            'reason':           self.state['reason'],
            'target_play':      self.state['target_play'],
        }

    def handle_bot_accusation(self, player_index: int, accusation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atomic bot accusation — bypasses the step-by-step UI flow.
        Bot evidence comes from server-verified metadata (is_illegal flags),
        so we trust it and go directly to adjudication.

        Input: {'crime_card': {...}, 'proof_card': {...}, 'violation_type': str}
        """
        # 1. Trigger if not already active
        if not self.state['active']:
            res = self.trigger(player_index)
            if not res['success']:
                return res

        crime = accusation.get('crime_card')
        proof = accusation.get('proof_card')
        violation = accusation.get('violation_type', 'REVOKE')

        if not crime:
            logger.error("[QAYD-BOT] Missing crime_card in accusation. Cancelling.")
            self._unlock_and_reset()
            return {'success': False, 'error': 'Missing crime_card'}

        # 2. Set state directly (skip menu/card select UI steps)
        # Use low-level update since this bypasses standard transitions
        self._update({
            'menu_option':    QaydMenuOption.REVEAL_CARDS,
            'violation_type': violation,
            'crime_card':     crime,
            'proof_card':     proof or crime,
            'step':           QaydStep.SELECT_CARD_2,  # Pre-adjudication
        })

        logger.info(
            f"[QAYD-BOT] Atomic accusation by {self.state['reporter']}: "
            f"crime={crime}, proof={proof}, violation={violation}"
        )

        # 3. Adjudicate immediately
        return self._adjudicate()
