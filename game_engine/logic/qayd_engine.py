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
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple

from game_engine.models.constants import GamePhase
from game_engine.logic.rules_validator import RulesValidator, ViolationType

logger = logging.getLogger(__name__)


# ─── Step Constants ───────────────────────────────────────────────────────────
class QaydStep:
    IDLE             = 'IDLE'
    MAIN_MENU        = 'MAIN_MENU'
    VIOLATION_SELECT = 'VIOLATION_SELECT'
    SELECT_CARD_1    = 'SELECT_CARD_1'   # Crime card (Pink Ring)
    SELECT_CARD_2    = 'SELECT_CARD_2'   # Proof card (Green Ring)
    ADJUDICATION     = 'ADJUDICATION'    # Backend validates
    RESULT           = 'RESULT'          # Verdict displayed


# ─── Main Menu Options ────────────────────────────────────────────────────────
class QaydMenuOption:
    REVEAL_CARDS = 'REVEAL_CARDS'   # كشف الأوراق
    WRONG_SAWA   = 'WRONG_SAWA'    # سوا خاطئ
    WRONG_AKKA   = 'WRONG_AKKA'    # أكة خاطئة


# ─── Timer Durations ──────────────────────────────────────────────────────────
TIMER_HUMAN = 60   # seconds
TIMER_AI    = 2    # seconds


def _empty_state() -> Dict[str, Any]:
    """Canonical empty state. Always the same structure."""
    return {
        'active':           False,
        'step':             QaydStep.IDLE,
        'reporter':         None,       # PlayerPosition string
        'reporter_is_bot':  False,
        'menu_option':      None,       # QaydMenuOption
        'violation_type':   None,       # ViolationType
        'crime_card':       None,       # dict with suit, rank, trick_idx, card_idx, played_by
        'proof_card':       None,       # same shape
        'verdict':          None,       # 'CORRECT' or 'WRONG'
        'verdict_message':  None,       # Arabic display string
        'loser_team':       None,       # 'us' or 'them'
        'penalty_points':   0,
        'timer_duration':   TIMER_HUMAN,
        'timer_start':      0,
        'crime_signature':  None,       # (trick_idx, card_idx) for Double Jeopardy
        # Legacy compat fields (read by get_game_state / frontend QaydState type)
        'status':           None,       # 'REVIEW' | 'RESOLVED'
        'reason':           None,
        'target_play':      None,
    }


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
    - This class now ONLY manages state transitions
    """

    def __init__(self, game):
        self.game = game
        self.state: Dict[str, Any] = _empty_state()
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

        # Lock & Transition
        self.game.is_locked = True
        self.game.phase = GamePhase.CHALLENGE.value
        self.game.timer_paused = True

        is_bot = getattr(player, 'is_bot', False)
        timer_dur = TIMER_AI if is_bot else TIMER_HUMAN

        self._update({
            'active':           True,
            'step':             QaydStep.MAIN_MENU,
            'reporter':         player.position,
            'reporter_is_bot':  is_bot,
            'timer_duration':   timer_dur,
            'timer_start':      time.time(),
            'status':           'REVIEW',
        })

        logger.info(f"[QAYD] Triggered by {player.position} (bot={is_bot}). Timer={timer_dur}s. Phase → CHALLENGE.")

        return {'success': True, 'qayd_state': self.state}

    def select_menu_option(self, option: str) -> Dict[str, Any]:
        """Step 1 (MAIN_MENU) → Step 2 (VIOLATION_SELECT)."""
        if self.state['step'] != QaydStep.MAIN_MENU:
            return {'success': False, 'error': f"Wrong step: {self.state['step']}"}

        self._update({'menu_option': option, 'step': QaydStep.VIOLATION_SELECT})
        return {'success': True, 'qayd_state': self.state}

    def select_violation(self, violation_type: str) -> Dict[str, Any]:
        """Step 2 (VIOLATION_SELECT) → Step 3 (SELECT_CARD_1). Also allows re-selection from SELECT_CARD_1/2."""
        if self.state['step'] not in (QaydStep.VIOLATION_SELECT, QaydStep.SELECT_CARD_1, QaydStep.SELECT_CARD_2):
            return {'success': False, 'error': f"Wrong step: {self.state['step']}"}

        self._update({'violation_type': violation_type, 'step': QaydStep.SELECT_CARD_1})
        return {'success': True, 'qayd_state': self.state}

    def select_crime_card(self, card_data: Dict) -> Dict[str, Any]:
        """Step 3 (SELECT_CARD_1) → Step 4 (SELECT_CARD_2). Also allows re-selection from SELECT_CARD_2."""
        if self.state['step'] not in (QaydStep.SELECT_CARD_1, QaydStep.SELECT_CARD_2):
            return {'success': False, 'error': f"Wrong step: {self.state['step']}"}

        if not self._validate_card_in_history(card_data):
            return {'success': False, 'error': 'Card not found in round history'}

        # --- LEDGER CHECK (Prevent Double Jeopardy) ---
        trick_idx = card_data.get('trick_idx')
        card_idx = card_data.get('card_idx')
        if trick_idx is not None and card_idx is not None:
            ledger_sig = f"{trick_idx}_{card_idx}"
            if ledger_sig in self.game.state.resolved_crimes:
                logger.warning(f"[QAYD] Selection blocked: Crime {ledger_sig} already resolved.")
                return {'success': False, 'error': 'This play has already been challenged.'}

        self._update({'crime_card': card_data, 'step': QaydStep.SELECT_CARD_2})
        return {'success': True, 'qayd_state': self.state}

    def select_proof_card(self, card_data: Dict) -> Dict[str, Any]:
        """Step 4 (SELECT_CARD_2) → ADJUDICATION → RESULT."""
        if self.state['step'] != QaydStep.SELECT_CARD_2:
            return {'success': False, 'error': f"Wrong step: {self.state['step']}"}

        if not self._validate_card_in_history(card_data):
            return {'success': False, 'error': 'Proof card not found in round history'}

        self._update({'proof_card': card_data, 'step': QaydStep.ADJUDICATION})
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
        self._update({
            'step': QaydStep.IDLE,
            'active': False,
            'status': 'RESOLVED',
        })

        self.game.is_locked = False
        self.game.timer_paused = False

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
        self._reset_state()

        # Restore phase
        if not was_result:
            phase_str = str(self.game.phase)
            if phase_str in (GamePhase.CHALLENGE.value, 'CHALLENGE'):
                self.game.phase = GamePhase.PLAYING.value
                logger.info("[QAYD] Phase reset CHALLENGE → PLAYING.")

        self.game.is_locked = False
        self.game.timer_paused = False

        return {'success': True}

    def reset(self):
        """Full reset for new round. Called by game.reset_round_state()."""
        self._reset_state()
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

        penalty = self._calculate_penalty()
        sig = (crime.get('trick_idx', -1), crime.get('card_idx', -1))

        self._update({
            'verdict': verdict,
            'verdict_message': verdict_msg,
            'loser_team': loser_team,
            'penalty_points': penalty,
            'reason': reason,
            'crime_signature': sig,
            'step': QaydStep.RESULT,
            'target_play': {
                'card': crime,
                'playedBy': offender_pos,
                'metadata': {'illegal_reason': reason},
            },
        })

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

        # Case 1: Card in Hand (trick_idx == -1)
        if trick_idx == -1:
            if not player_pos:
                return False
            player = next((p for p in self.game.players if p.position == player_pos), None)
            if not player or not player.hand:
                return False
            return 0 <= card_idx < len(player.hand)

        # Case 2: Card currently on Table
        if trick_idx == len(self.game.round_history):
            return 0 <= card_idx < len(self.game.table_cards)

        # Case 3: Card in confirmed History
        if 0 <= trick_idx < len(self.game.round_history):
            trick = self.game.round_history[trick_idx]
            cards = trick.get('cards', [])
            if 0 <= card_idx < len(cards):
                return True
            played_by = trick.get('playedBy', [])
            if 0 <= card_idx < len(played_by):
                return True
            return False

        return False

    def _calculate_penalty(self) -> int:
        """
        SUN/ASHKAL = 26 base, HOKUM = 16 base.
        Multiplied by doubling level.
        NOTE: Project points are NOT added here. (FIX for BUG-03)
        apply_qayd_penalty adds them once.
        """
        mode_str = str(self.game.game_mode or '').upper()
        is_sun = ('SUN' in mode_str) or ('ASHKAL' in mode_str)
        base = 26 if is_sun else 16

        dl = getattr(self.game, 'doubling_level', 1) or 1
        if dl >= 2:
            base *= dl

        return base

    # ══════════════════════════════════════════════════════════════════════════
    #  INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _update(self, patch: Dict[str, Any]):
        """In-place update. Never reassign self.state."""
        self.state.update(patch)

    def _reset_state(self):
        """Reset to idle. Preserves dict identity."""
        self.state.clear()
        self.state.update(_empty_state())

    def _unlock_and_reset(self):
        """Reset state AND unlock game + restore phase."""
        self._reset_state()
        self.game.is_locked = False
        self.game.timer_paused = False
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
        Orchestrate a full accusation sequence for a Bot.
        Input: {'crime_card': ..., 'proof_card': ..., 'violation_type': ...}
        """
        # 1. Trigger if needed
        if not self.state['active']:
             res = self.trigger(player_index)
             if not res['success']: return res
        
        # 2. Select VIOLATION (Skip MENU)
        if self.state['step'] == QaydStep.MAIN_MENU:
             self.select_menu_option(QaydMenuOption.REVEAL_CARDS)
             
        # 3. Select Violation Type
        v_type = accusation.get('violation_type', 'REVOKE')
        res = self.select_violation(v_type)
        if not res['success']: return res
        
        # 4. Select Crime Card
        crime = accusation.get('crime_card')
        if not crime: return {'success': False, 'error': 'Missing crime_card'}
        res = self.select_crime_card(crime)
        if not res['success']: return res
        
        # 5. Select Proof Card
        proof = accusation.get('proof_card')
        if not proof: return {'success': False, 'error': 'Missing proof_card'}
        res = self.select_proof_card(proof)
        
        return res

