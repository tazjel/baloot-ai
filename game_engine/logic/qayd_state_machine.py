"""
Qayd State Machine - Core State Transitions
===========================================

This module handles the state transitions and data structure for the Qayd system.
It is purely functional and does not depend on the Game object directly,
except for context passed into methods.
"""

import time
from typing import Dict, Any, Optional

class QaydStep:
    IDLE             = 'IDLE'
    MAIN_MENU        = 'MAIN_MENU'
    VIOLATION_SELECT = 'VIOLATION_SELECT'
    SELECT_CARD_1    = 'SELECT_CARD_1'   # Crime card (Pink Ring)
    SELECT_CARD_2    = 'SELECT_CARD_2'   # Proof card (Green Ring)
    ADJUDICATION     = 'ADJUDICATION'    # Backend validates
    RESULT           = 'RESULT'          # Verdict displayed


class QaydMenuOption:
    REVEAL_CARDS = 'REVEAL_CARDS'   # كشف الأوراق
    WRONG_SAWA   = 'WRONG_SAWA'    # سوا خاطئ
    WRONG_AKKA   = 'WRONG_AKKA'    # أكة خاطئة


# ─── Timer Durations ──────────────────────────────────────────────────────────
TIMER_HUMAN = 60   # seconds
TIMER_AI    = 2    # seconds


def empty_qayd_state() -> Dict[str, Any]:
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


class QaydStateMachine:
    """
    Manages state transitions for Qayd.
    Does NOT contain business logic for validation or penalties.
    """

    def __init__(self):
        self.state = empty_qayd_state()

    def update(self, patch: Dict[str, Any]):
        """In-place update."""
        self.state.update(patch)

    def reset(self):
        """Reset to idle."""
        self.state.clear()
        self.state.update(empty_qayd_state())

    def start_session(self, reporter_pos: str, is_bot: bool):
        """Transition IDLE -> MAIN_MENU"""
        timer_dur = TIMER_AI if is_bot else TIMER_HUMAN
        self.update({
            'active':           True,
            'step':             QaydStep.MAIN_MENU,
            'reporter':         reporter_pos,
            'reporter_is_bot':  is_bot,
            'timer_duration':   timer_dur,
            'timer_start':      time.time(),
            'status':           'REVIEW',
        })
        return timer_dur

    def to_violation_select(self, option: str):
        """Transition MAIN_MENU -> VIOLATION_SELECT"""
        self.update({'menu_option': option, 'step': QaydStep.VIOLATION_SELECT})

    def to_card_select_1(self, violation_type: str):
        """Transition VIOLATION_SELECT -> SELECT_CARD_1"""
        self.update({'violation_type': violation_type, 'step': QaydStep.SELECT_CARD_1})

    def to_card_select_2(self, crime_card: Dict):
        """Transition SELECT_CARD_1 -> SELECT_CARD_2"""
        self.update({'crime_card': crime_card, 'step': QaydStep.SELECT_CARD_2})

    def to_adjudication(self, proof_card: Dict):
        """Transition SELECT_CARD_2 -> ADJUDICATION"""
        self.update({'proof_card': proof_card, 'step': QaydStep.ADJUDICATION})

    def to_result(self, verdict: str, verdict_msg: str, loser_team: str, 
                 penalty: int, reason: str, sig: tuple, target_play: Dict):
        """Transition ADJUDICATION -> RESULT"""
        self.update({
            'verdict': verdict,
            'verdict_message': verdict_msg,
            'loser_team': loser_team,
            'penalty_points': penalty,
            'reason': reason,
            'crime_signature': sig,
            'step': QaydStep.RESULT,
            'target_play': target_play,
        })

    def resolve(self):
        """Transition RESULT -> IDLE (RESOLVED)"""
        self.update({
            'step': QaydStep.IDLE,
            'active': False,
            'status': 'RESOLVED',
        })
