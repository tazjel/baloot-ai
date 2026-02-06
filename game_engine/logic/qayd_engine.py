"""
QaydEngine — Unified Forensic Challenge System (Kammelna Spec)
==============================================================

Replaces:
  - qayd_manager.py (no longer used)
  - challenge_phase.py Qayd methods (extracted)
  - trick_manager.py propose_qayd/confirm_qayd/cancel_qayd (extracted)

State Machine:
  IDLE → MAIN_MENU → VIOLATION_SELECT → SELECT_CARD_1 → SELECT_CARD_2 → ADJUDICATION → RESULT → IDLE

Single source of truth for all Qayd state. Game.qayd_state is an alias
to QaydEngine.state (same dict object, never reassigned).
"""

import time
import logging
import copy
from typing import Dict, List, Any, Optional, Tuple

from game_engine.models.constants import (
    GamePhase, ORDER_HOKUM, ORDER_SUN,
    POINT_VALUES_SUN, POINT_VALUES_HOKUM
)

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


# ─── Violation Types ──────────────────────────────────────────────────────────
class ViolationType:
    REVOKE           = 'REVOKE'           # قاطع — Failure to follow suit
    TRUMP_IN_DOUBLE  = 'TRUMP_IN_DOUBLE'  # ربع في الدبل — Illegal trump in doubled game
    NO_OVERTRUMP     = 'NO_OVERTRUMP'     # ما كبر بحكم — Playing lower trump when holding higher
    NO_TRUMP         = 'NO_TRUMP'         # ما دق بحكم — Not trumping when void in suit


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
    Unified Qayd (Forensic Challenge) Engine.

    Usage:
        engine = QaydEngine(game)
        game.qayd_state = engine.state   # alias — NEVER reassign game.qayd_state

    All mutations go through engine methods. The dict is mutated IN-PLACE
    so all aliases remain valid.
    """

    def __init__(self, game):
        self.game = game
        self.state: Dict[str, Any] = _empty_state()
        self.ignored_crimes: set = set()   # (trick_idx, card_idx) tuples — Double Jeopardy

    # ══════════════════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════

    def trigger(self, player_index: int) -> Dict[str, Any]:
        """
        Step 0 → Step 1 (MAIN_MENU).
        Called when a player presses the Qayd button.
        Locks the game and pauses timers.
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

        # Bot Fast-Path — skip UI, go straight to auto-detect + confirm
        if is_bot:
            return self._bot_auto_accuse(player_index)

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

        # Add crime to ignore list
        sig = self.state.get('crime_signature')
        if sig:
            self.ignored_crimes.add(sig)

        # Apply penalty through game (ends the round)
        self.game.apply_qayd_penalty(loser_team, winner_team)

        # Mark resolved (state may have been partially reset by apply_qayd_penalty)
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

        sig = self.state.get('crime_signature')
        if sig:
            self.ignored_crimes.add(sig)
            logger.info(f"[QAYD] Crime {sig} added to ignore list (cancelled).")

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
        self.ignored_crimes.clear()

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
    #  LEGACY COMPAT: Direct accusation (used by old bot_agent / auto_play)
    # ══════════════════════════════════════════════════════════════════════════

    def handle_legacy_accusation(self, player_index: int, accusation: Dict) -> Dict[str, Any]:
        """
        Accepts old-style {crime_card, proof_card, violation_type} payload.
        Fast-paths through the state machine.
        """
        crime_card = accusation.get('crime_card')
        proof_card = accusation.get('proof_card')
        qayd_type = accusation.get('qayd_type', accusation.get('violation_type', 'REVOKE'))

        # Ensure triggered
        if not self.state['active']:
            result = self.trigger(player_index)
            if not result.get('success'):
                return result

        if self.state['step'] in (QaydStep.MAIN_MENU, QaydStep.IDLE):
            self.select_menu_option('REVEAL_CARDS')

        if self.state['step'] == QaydStep.VIOLATION_SELECT:
            self.select_violation(qayd_type)

        if self.state['step'] == QaydStep.SELECT_CARD_1 and crime_card:
            self.select_crime_card(crime_card)

        if self.state['step'] == QaydStep.SELECT_CARD_2 and proof_card:
            return self.select_proof_card(proof_card)

        return {'success': True, 'qayd_state': self.state}

    # ══════════════════════════════════════════════════════════════════════════
    #  BOT AUTO-ACCUSATION (Metadata-based detection)
    # ══════════════════════════════════════════════════════════════════════════

    def _bot_auto_accuse(self, reporter_index: int) -> Dict[str, Any]:
        """Bots skip the 5-step UI; scan for is_illegal metadata flags."""
        crime_data = None

        # Search table_cards (current trick) - FIFO (First Crime Wins)
        for i, play in enumerate(self.game.table_cards):
            meta = play.get('metadata') or {}
            if meta.get('is_illegal'):
                # Note: trick_idx is len(round_history)
                trick_idx = len(self.game.round_history)
                card = play['card']
                crime_data = {
                    'suit': card.suit if hasattr(card, 'suit') else card.get('suit'),
                    'rank': card.rank if hasattr(card, 'rank') else card.get('rank'),
                    'trick_idx': trick_idx,
                    'card_idx': i,
                    'played_by': play.get('playedBy'),
                }
                meta['is_illegal'] = False  # Clear flag
                break

        # Search ALL completed tricks in forward order (FIFO)
        if not crime_data and self.game.round_history:
            for t_idx, trick in enumerate(self.game.round_history):
                 metas = trick.get('metadata') or []
                 for i, meta in enumerate(metas):
                      if meta and meta.get('is_illegal'):
                           cards = trick.get('cards', [])
                           c = cards[i] if i < len(cards) else {}
                           # Cards may be {card: dict, playedBy: str} or flat dicts
                           card_inner = c.get('card', c) if isinstance(c, dict) else c
                           played_by_list = trick.get('playedBy', [])
                           played_by = c.get('playedBy') if isinstance(c, dict) and 'playedBy' in c else (
                               played_by_list[i] if i < len(played_by_list) else None
                           )
                           crime_data = {
                                'suit': card_inner.get('suit') if isinstance(card_inner, dict) else getattr(card_inner, 'suit', None),
                                'rank': card_inner.get('rank') if isinstance(card_inner, dict) else getattr(card_inner, 'rank', None),
                                'trick_idx': t_idx,
                                'card_idx': i,
                                'played_by': played_by,
                           }
                           meta['is_illegal'] = False # Clear flag to prevent double jeopardy
                           break
                 if crime_data:
                      break

        # Double Jeopardy check
        if crime_data:
            sig = (crime_data['trick_idx'], crime_data['card_idx'])
            if sig in self.ignored_crimes:
                logger.info(f"[QAYD] Bot ignoring already-cancelled crime: {sig}")
                self._unlock_and_reset()
                return {'success': False, 'error': 'Double Jeopardy'}

        if not crime_data:
            logger.info("[QAYD] Bot found no illegal cards. Cancelling.")
            self._unlock_and_reset()
            return {'success': False, 'error': 'No crime detected'}

        # Determine verdict
        offender_pos = crime_data['played_by']
        offender = next((p for p in self.game.players if p.position == offender_pos), None)
        reporter = self.game.players[reporter_index]

        if offender:
            loser_team = offender.team
            verdict = 'CORRECT'
            verdict_msg = 'قيد صحيح'
            reason = f"Bot auto-detect: {offender_pos} played illegal card"
        else:
            loser_team = reporter.team
            verdict = 'WRONG'
            verdict_msg = 'قيد خاطئ'
            reason = "Bot accusation failed — offender not found"

        penalty = self._calculate_penalty()
        sig = (crime_data['trick_idx'], crime_data['card_idx'])

        self._update({
            'crime_card': crime_data,
            'proof_card': None,
            'violation_type': ViolationType.REVOKE,
            'verdict': verdict,
            'verdict_message': verdict_msg,
            'loser_team': loser_team,
            'penalty_points': penalty,
            'crime_signature': sig,
            'step': QaydStep.RESULT,
            'reason': reason,
            'target_play': {
                'card': crime_data,
                'playedBy': offender_pos,
                'metadata': {'illegal_reason': reason},
            },
        })

        logger.info(f"[QAYD] Bot auto-accused: {verdict}. Penalty={penalty}. Loser={loser_team}")

        # Bot waits for timer to expire before confirming (so users see the result)
        return {'success': True, 'qayd_state': self.state}

    # ══════════════════════════════════════════════════════════════════════════
    #  ADJUDICATION (Human forensic path)
    # ══════════════════════════════════════════════════════════════════════════

    def _adjudicate(self) -> Dict[str, Any]:
        """Validate the accusation after both cards selected."""
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

        is_guilty = False
        reason = "Move appears legal."

        if violation == ViolationType.REVOKE and proof:
            is_guilty, reason = self._validate_revoke(crime, proof, offender_pos)
        elif violation == ViolationType.NO_TRUMP and proof:
            is_guilty, reason = self._validate_no_trump(crime, proof, offender_pos)
        elif violation == ViolationType.NO_OVERTRUMP and proof:
            is_guilty, reason = self._validate_no_overtrump(crime, proof, offender_pos)
        elif violation == ViolationType.TRUMP_IN_DOUBLE:
            is_guilty, reason = self._validate_via_metadata(crime)
        else:
            is_guilty, reason = self._validate_via_metadata(crime)

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
    #  VALIDATION HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _validate_revoke(self, crime: Dict, proof: Dict, offender_pos: str) -> Tuple[bool, str]:
        """Revoke: offender played wrong suit, proof shows they had the led suit."""
        crime_trick_idx = crime.get('trick_idx', -1)
        proof_trick_idx = proof.get('trick_idx', -1)

        if crime_trick_idx == len(self.game.round_history):
            # Construct virtual trick from current table (already in {card, playedBy} format)
            crime_trick = {
                'cards': [{'card': c['card'], 'playedBy': c['playedBy']} for c in self.game.table_cards],
                'playedBy': [c['playedBy'] for c in self.game.table_cards],
                'metadata': [c.get('metadata', {}) for c in self.game.table_cards]
            }
        elif 0 <= crime_trick_idx < len(self.game.round_history):
            crime_trick = self.game.round_history[crime_trick_idx]
        else:
            return False, "Crime trick not found in history."

        led_suit = self._get_led_suit(crime_trick)

        if not led_suit:
            return False, "Cannot determine led suit."

        crime_suit = crime.get('suit')
        proof_suit = proof.get('suit')

        if crime_suit == led_suit:
            return False, "Crime card follows suit — not a revoke."

        if proof_suit != led_suit:
            return False, "Proof card is not the led suit."

        proof_played_by = proof.get('played_by')
        if proof_played_by != offender_pos:
            return False, "Proof card was not played by the accused."

        # Pass if proof is in hand (trick_idx == -1)
        if proof_trick_idx >= 0 and proof_trick_idx <= crime_trick_idx:
            return False, "Proof card was played before or at the same time as the crime."

        return True, f"قاطع: {offender_pos} held {led_suit} but played {crime_suit}."

    def _validate_no_trump(self, crime: Dict, proof: Dict, offender_pos: str) -> Tuple[bool, str]:
        """NO_TRUMP: Offender didn't play trump when they had it."""
        mode = str(self.game.game_mode or '').upper()
        if 'HOKUM' not in mode:
            return False, "NO_TRUMP only applies to Hokum."

        proof_suit = proof.get('suit')
        if proof_suit != self.game.trump_suit:
            return False, "Proof card is not trump suit."

        crime_suit = crime.get('suit')
        if crime_suit == self.game.trump_suit:
            return False, "Crime card IS trump — they did trump."

        proof_played_by = proof.get('played_by')
        if proof_played_by != offender_pos:
            return False, "Proof card not played by accused."

        return True, f"ما دق بحكم: {offender_pos} had trump but didn't play it."

    def _validate_no_overtrump(self, crime: Dict, proof: Dict, offender_pos: str) -> Tuple[bool, str]:
        """NO_OVERTRUMP: Offender played lower trump when holding higher."""
        mode = str(self.game.game_mode or '').upper()
        if 'HOKUM' not in mode:
            return False, "NO_OVERTRUMP only applies to Hokum."

        crime_suit = crime.get('suit')
        proof_suit = proof.get('suit')

        if crime_suit != self.game.trump_suit or proof_suit != self.game.trump_suit:
            return False, "Both cards must be trump for overtrump violation."

        proof_played_by = proof.get('played_by')
        if proof_played_by != offender_pos:
            return False, "Proof card not played by accused."

        try:
            crime_strength = ORDER_HOKUM.index(crime.get('rank'))
            proof_strength = ORDER_HOKUM.index(proof.get('rank'))
        except ValueError:
            return False, "Invalid card rank."

        if proof_strength <= crime_strength:
            return False, "Proof card is not higher than crime card."

        return True, f"ما كبر بحكم: {offender_pos} had higher trump but played lower."

    def _validate_via_metadata(self, crime: Dict) -> Tuple[bool, str]:
        """Fallback: Check if the card was flagged as illegal by the engine."""
        trick_idx = crime.get('trick_idx', -1)
        card_idx = crime.get('card_idx', -1)

        # Check current table
        if trick_idx == len(self.game.round_history):
            if 0 <= card_idx < len(self.game.table_cards):
                meta = self.game.table_cards[card_idx].get('metadata') or {}
                if meta.get('is_illegal'):
                    reason = meta.get('illegal_reason', 'Rule violation detected by engine')
                    return True, reason

        # Check round history — metadata is a separate array parallel to cards
        if 0 <= trick_idx < len(self.game.round_history):
            trick = self.game.round_history[trick_idx]
            metas = trick.get('metadata') or []
            if 0 <= card_idx < len(metas) and metas[card_idx]:
                meta_entry = metas[card_idx]
                if isinstance(meta_entry, dict) and meta_entry.get('is_illegal'):
                    reason = meta_entry.get('illegal_reason', 'Rule violation detected')
                    return True, reason

        return False, "Move appears legal."

    def _validate_card_in_history(self, card_data: Dict) -> bool:
        """Check that a card reference points to a real card (History, Table, or Hand)."""
        trick_idx = card_data.get('trick_idx', -1)
        card_idx = card_data.get('card_idx', -1)
        player_pos = card_data.get('played_by')

        # Case 1: Card in Hand (trick_idx == -1)
        # Needed for 'Proof' cards when hands are revealed
        if trick_idx == -1:
            if not player_pos:
                return False
            player = next((p for p in self.game.players if p.position == player_pos), None)
            if not player or not player.hand:
                return False
            return 0 <= card_idx < len(player.hand)

        # Case 2: Card currently on Table (In-progress trick)
        if trick_idx == len(self.game.round_history):
            return 0 <= card_idx < len(self.game.table_cards)

        # Case 3: Card in confirmed History
        if 0 <= trick_idx < len(self.game.round_history):
            trick = self.game.round_history[trick_idx]
            cards = trick.get('cards', [])
            if 0 <= card_idx < len(cards):
                return True
            # Also check via playedBy array length as fallback
            played_by = trick.get('playedBy', [])
            if 0 <= card_idx < len(played_by):
                return True
            return False

        return False

    def _get_led_suit(self, trick: Dict) -> Optional[str]:
        """Extract the led suit from a trick record.
        Cards may be flat dicts {suit, rank} or wrapped {card: {suit, rank}, playedBy: str}.
        """
        cards = trick.get('cards', [])
        if not cards:
            return None
        first = cards[0]
        if isinstance(first, dict):
            # Wrapped format: {card: {...}, playedBy: ...}
            if 'card' in first:
                inner = first['card']
                return inner.get('suit') if isinstance(inner, dict) else getattr(inner, 'suit', None)
            return first.get('suit')
        if hasattr(first, 'suit'):
            return first.suit
        return None

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
