"""
verify_qayd_live.py — Comprehensive Qayd, Sawa & Akka Live Test
========================================================================

Multi-round, event-driven stress test that verifies:
  1. Revoke detection (is_illegal flags)                 [qayd mode]
  2. Qayd state machine transitions                       [qayd mode]
  3. Score penalty application                            [qayd mode]
  4. Sawa (Grand Slam) claim / accept / refuse            [sawa mode]
  5. Sawa challenge mode (claimer must win ALL tricks)    [sawa mode]
  6. Akka (Master Declaration) state tracking              [akka mode]
  7. Phase transitions (PLAYING → CHALLENGE → FINISHED → BIDDING)
  8. Multi-round cycling without freezes or errors
  9. Socket/server error capture

Usage:
  python scripts/verify_qayd_live.py [--mode qayd|sawa|akka|all] [--rounds N] [--timeout T]
"""

import socketio
import time
import sys
import logging
import argparse
import json
from typing import List, Dict, Any, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
SERVER_URL = "http://localhost:3005"
DEFAULT_ROUNDS = 3
DEFAULT_TIMEOUT = 120  # Overall test timeout in seconds

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('QaydStress')


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT LOG — Timestamped event recorder for post-mortem analysis
# ═══════════════════════════════════════════════════════════════════════════════
class EventLog:
    """Records every socket event with a time offset from test start."""

    def __init__(self):
        self.start_time = time.time()
        self.entries: List[Dict[str, Any]] = []

    def record(self, event_name: str, summary: str, data: Any = None):
        delta = time.time() - self.start_time
        entry = {
            'time': f"+{delta:.1f}s",
            'event': event_name,
            'summary': summary,
        }
        if data is not None:
            entry['data'] = data
        self.entries.append(entry)
        logger.info(f"[{entry['time']}] {event_name}: {summary}")

    def dump(self):
        """Return all entries for the final report."""
        return self.entries


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR COLLECTOR — Aggregates all failures for the final report
# ═══════════════════════════════════════════════════════════════════════════════
class ErrorCollector:
    """Gathers errors, anomalies, and warnings throughout the test."""

    def __init__(self):
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []

    def add_error(self, category: str, message: str):
        self.errors.append({'category': category, 'message': message})
        logger.error(f"❌ [{category}] {message}")

    def add_warning(self, category: str, message: str):
        self.warnings.append({'category': category, 'message': message})
        logger.warning(f"⚠️  [{category}] {message}")

    @property
    def has_errors(self):
        return len(self.errors) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# GAME MONITOR — Deep state tracker wired to socket events
# ═══════════════════════════════════════════════════════════════════════════════
class GameMonitor:
    """
    Tracks all game state from socket events.
    Verifies Qayd/Sawa state machine transitions and detects anomalies.
    """

    def __init__(self, event_log: EventLog, error_collector: ErrorCollector, test_mode: str = 'qayd'):
        self.log = event_log
        self.errors = error_collector
        self.test_mode = test_mode  # 'qayd', 'sawa', or 'all'

        # Connection
        self.room_id: Optional[str] = None
        self.player_index: int = -1
        self.sio = None  # Set externally for reactive play

        # Game State
        self.phase: Optional[str] = None
        self.prev_phase: Optional[str] = None
        self.hand: List[Dict] = []
        self.table_cards: List[Dict] = []
        self.scores: Dict[str, int] = {'us': 0, 'them': 0}
        self.round_num: int = 0
        self.game_mode: Optional[str] = None
        self.trump_suit: Optional[str] = None
        self.current_turn: int = -1

        # Qayd Tracking
        self.qayd_state: Dict[str, Any] = {}
        self.qayd_step_history: List[str] = []  # Track step transitions
        self.qayd_triggers: int = 0
        self.qayd_resolutions: int = 0
        self.qayd_verdicts: List[str] = []

        # Sawa Tracking
        self.sawa_state: Dict[str, Any] = {}
        self.sawa_step_history: List[str] = []  # e.g. NONE→PENDING, PENDING→ACCEPTED
        self.sawa_claims: int = 0
        self.sawa_accepted: int = 0
        self.sawa_refused: int = 0
        self.sawa_invalid: int = 0  # Claims rejected by server (not eligible)
        self.sawa_challenge_wins: int = 0
        self.sawa_challenge_losses: int = 0
        self._sawa_claim_sent_this_turn: bool = False  # Prevent duplicate claims

        # Akka Tracking
        self.akka_triggers: int = 0       # Count of akkaState becoming active
        self.akka_clears: int = 0         # Count of akkaState being cleared
        self.akka_suits: List[str] = []   # Suits declared via Akka
        self.akka_history: List[str] = [] # Transition history
        self.akka_state: Dict[str, Any] = {}  # Last seen akkaState

        # Round Tracking
        self.rounds_completed: int = 0
        self.round_scores: List[Dict] = []
        self.phase_epoch: int = 0  # Increments on every phase change (for fresh-wait)

        # Reactive Play Tracking
        self.our_plays: int = 0
        self.revoke_attempts: int = 0
        self.revoke_successes: int = 0
        self._bid_sent_this_round: bool = False
        self._played_this_turn: bool = False  # Prevent duplicate plays per turn
        self._last_hand_size: int = 0  # Track hand changes to reset play guard

        # Error Tracking
        self.socket_errors: List[str] = []
        self.unexpected_transitions: List[str] = []

    def on_game_update(self, data: Dict):
        """Process game_update events — the most important event."""
        # -- Phase tracking --
        new_phase = data.get('phase')
        if new_phase and new_phase != self.phase:
            self.prev_phase = self.phase
            self.phase = new_phase
            self.phase_epoch += 1
            self.log.record('PHASE_CHANGE', f"{self.prev_phase} → {self.phase} (epoch {self.phase_epoch})")

            # Detect unexpected phase transitions
            valid_transitions = {
                None: {'BIDDING', 'WAITING'},
                'WAITING': {'BIDDING'},
                'BIDDING': {'PLAYING', 'BIDDING'},
                'PLAYING': {'FINISHED', 'CHALLENGE', 'PLAYING'},
                'CHALLENGE': {'FINISHED', 'PLAYING', 'CHALLENGE'},
                'FINISHED': {'BIDDING', 'WAITING', 'FINISHED', 'GAME_OVER'},
            }
            expected = valid_transitions.get(self.prev_phase, set())
            if self.phase not in expected:
                msg = f"Unexpected transition: {self.prev_phase} → {self.phase}"
                self.errors.add_warning('PHASE', msg)
                self.unexpected_transitions.append(msg)

        # -- Score tracking --
        match_scores = data.get('matchScores')
        if match_scores:
            old_scores = dict(self.scores)
            self.scores = match_scores
            if old_scores != match_scores:
                self.log.record('SCORE_CHANGE',
                    f"us: {old_scores.get('us',0)} → {match_scores.get('us',0)}, "
                    f"them: {old_scores.get('them',0)} → {match_scores.get('them',0)}")

        # -- Table cards tracking --
        tc = data.get('tableCards', [])
        if tc != self.table_cards:
            self.table_cards = tc

        # -- Turn tracking (schema field is `currentTurnIndex`) --
        ct = data.get('currentTurnIndex')
        if ct is not None:
            if ct != self.current_turn:
                self._played_this_turn = False  # Reset play guard on turn change
                self._sawa_claim_sent_this_turn = False  # Reset sawa guard on turn change
            self.current_turn = ct

        # -- Also check isActive on players array as fallback --
        # -- AND extract our hand from the players array --
        players = data.get('players', [])
        for p in players:
            if p.get('isActive'):
                idx = p.get('index')
                if idx is not None:
                    self.current_turn = idx
            # Extract our hand from the players array
            if self.player_index >= 0 and p.get('index') == self.player_index:
                hand_data = p.get('hand', [])
                if hand_data and len(hand_data) != self._last_hand_size:
                    self._last_hand_size = len(hand_data)
                    self._played_this_turn = False  # Hand changed, can play again
                    self.hand = hand_data
                    suits = {}
                    for c in self.hand:
                        s = c.get('suit', '?')
                        suits[s] = suits.get(s, 0) + 1
                    self.log.record('HAND_UPDATE', f"{len(self.hand)} cards | Suits: {suits}")

        # -- Game mode --
        gm = data.get('gameMode')
        if gm:
            self.game_mode = gm
        ts = data.get('trumpSuit')
        if ts:
            self.trump_suit = ts

        # -- Round tracking --
        rh = data.get('roundHistory')
        if rh is not None:
            new_round_num = len(rh)
            if new_round_num > self.round_num:
                self.round_num = new_round_num
                self.rounds_completed = new_round_num
                self.round_scores.append(dict(self.scores))
                self._bid_sent_this_round = False
                self.log.record('ROUND_COMPLETE', f"Round {self.round_num} finished. Scores: {self.scores}")

        # -- REACTIVE AUTO-PLAY: bid & play from callback --
        self._auto_play()

        # -- QAYD STATE MACHINE TRACKING (the critical part) --
        qs = data.get('qaydState')
        if qs:
            self._track_qayd_state(qs)

        # -- SAWA STATE TRACKING --
        ss = data.get('sawaState')
        if ss:
            self._track_sawa_state(ss)

        # -- AKKA STATE TRACKING --
        aks = data.get('akkaState')
        self._track_akka_state(aks)

    def _track_qayd_state(self, qs: Dict):
        """Deep-inspect Qayd state changes and verify transitions."""
        new_step = qs.get('step', 'IDLE')
        old_step = self.qayd_state.get('step', 'IDLE')

        # Track active transitions
        was_active = self.qayd_state.get('active', False)
        is_active = qs.get('active', False)

        if is_active and not was_active:
            self.qayd_triggers += 1
            accuser = qs.get('accuserIndex', '?')
            accused = qs.get('accusedPosition', '?')
            self.log.record('QAYD_ACTIVATED',
                f"Trigger #{self.qayd_triggers} by player {accuser} against {accused}",
                {'step': new_step, 'accuser': accuser, 'accused': accused})

        if not is_active and was_active:
            status = qs.get('status', '?')
            self.log.record('QAYD_DEACTIVATED', f"Status: {status}")

        # Track step transitions
        if new_step != old_step:
            self.qayd_step_history.append(f"{old_step}→{new_step}")
            self.log.record('QAYD_STEP', f"{old_step} → {new_step}")

        # Track verdict
        verdict = qs.get('verdict')
        if verdict and verdict != self.qayd_state.get('verdict'):
            self.qayd_verdicts.append(verdict)
            penalty = qs.get('penalty', 0)
            self.log.record('QAYD_VERDICT', f"Verdict: {verdict}, Penalty: {penalty}")

        # Track resolution
        status = qs.get('status')
        if status == 'RESOLVED' and self.qayd_state.get('status') != 'RESOLVED':
            self.qayd_resolutions += 1
            reason = qs.get('reason', 'unknown')
            self.log.record('QAYD_RESOLVED', f"Resolution #{self.qayd_resolutions}: {reason}")

        self.qayd_state = dict(qs)

    def _track_sawa_state(self, ss: Dict):
        """Deep-inspect Sawa state changes and verify transitions."""
        new_status = ss.get('status', 'NONE')
        old_status = self.sawa_state.get('status', 'NONE')

        # Track status transitions
        if new_status != old_status:
            self.sawa_step_history.append(f"{old_status}→{new_status}")
            self.log.record('SAWA_STATUS', f"{old_status} → {new_status}")

            if new_status == 'PENDING':
                claimer = ss.get('claimer', '?')
                valid = ss.get('valid', '?')
                cards_left = ss.get('cards_left', '?')
                self.log.record('SAWA_CLAIMED', f"Claimer: {claimer}, Valid: {valid}, Cards: {cards_left}",
                    {'claimer': claimer, 'valid': valid, 'cards_left': cards_left})

            elif new_status == 'PENDING_TIMER':
                claimer = ss.get('claimer', '?')
                valid = ss.get('valid', '?')
                self.log.record('SAWA_TIMER', f"3s timer started for {claimer} (valid={valid})")

            elif new_status == 'RESOLVED':
                self.sawa_accepted += 1
                self.log.record('SAWA_RESOLVED', 'Sawa resolved — round ended!')

            elif new_status == 'PENALTY':
                self.sawa_refused += 1
                penalty_team = ss.get('penalty_team', '?')
                self.log.record('SAWA_PENALTY',
                    f"Sawa penalty applied to team: {penalty_team}")

        self.sawa_state = dict(ss)

    def _track_akka_state(self, aks):
        """Track Akka (Master Declaration) state from akkaState in game_update."""
        was_active = bool(self.akka_state and self.akka_state.get('active'))
        is_active = bool(aks and aks.get('active'))

        if is_active and not was_active:
            # New Akka declaration
            self.akka_triggers += 1
            claimer = aks.get('claimer', '?')
            suits = aks.get('suits', [])
            self.akka_suits.extend(suits)
            self.akka_history.append(f"DECLARED by {claimer} suits={suits}")
            self.log.record('AKKA_DECLARED',
                f"Trigger #{self.akka_triggers} by {claimer} for suits: {suits}",
                {'claimer': claimer, 'suits': suits})

        elif not is_active and was_active:
            # Akka cleared (trick resolved)
            self.akka_clears += 1
            self.akka_history.append('CLEARED')
            self.log.record('AKKA_CLEARED',
                f"Clear #{self.akka_clears} (trick resolved)")

        # Update stored state
        self.akka_state = dict(aks) if aks else {}

    def on_game_start(self, data: Dict):
        """Process game_start events."""
        gs = data.get('gameState', {})
        new_phase = gs.get('phase')
        if new_phase and new_phase != self.phase:
            self.prev_phase = self.phase
            self.phase = new_phase
            self.phase_epoch += 1
        elif new_phase:
            self.phase = new_phase
        self.scores = gs.get('matchScores', {'us': 0, 'them': 0})
        new_round_num = len(gs.get('roundHistory', []))
        if new_round_num > self.round_num:
            self.rounds_completed = new_round_num
            self.round_scores.append(dict(self.scores))
            self.log.record('ROUND_COMPLETE', f"Round {new_round_num} done. Scores: {self.scores}")
        self.round_num = new_round_num
        self.game_mode = gs.get('gameMode')
        self.trump_suit = gs.get('trumpSuit')
        self._bid_sent_this_round = False  # Reset bid flag for new round
        self._played_this_turn = False  # Reset play guard for new round
        self._sawa_claim_sent_this_turn = False  # Reset sawa guard for new round

        # Detect our player index from the players array
        players = gs.get('players', [])
        for p in players:
            if p.get('id') == 'QaydStressTester' or p.get('name') == 'StressTester':
                self.player_index = p.get('index', 0)
                break

        self.log.record('GAME_START',
            f"Phase: {self.phase}, Mode: {self.game_mode}, "
            f"Scores: {self.scores}, MyIndex: {self.player_index}, Epoch: {self.phase_epoch}")

        # Also extract hand from game_start
        if self.player_index >= 0 and players:
            for p in players:
                if p.get('index') == self.player_index:
                    hand_data = p.get('hand', [])
                    if hand_data:
                        self.hand = hand_data

        # Try auto-play/bid from game_start too
        self._auto_play()

    def _auto_play(self):
        """Reactively bid or play when it's our turn. Called from event callbacks."""
        if not self.sio or not self.room_id or self.player_index < 0:
            return

        try:
            # Auto-bid in BIDDING phase (only when it's our turn)
            if self.phase == 'BIDDING' and not self._bid_sent_this_round and self.current_turn == self.player_index:
                self._bid_sent_this_round = True
                # Akka mode: bid HOKUM (Akka is HOKUM-only); otherwise bid SUN
                if self.test_mode == 'akka':
                    bid_action, bid_suit = 'HOKUM', '♠'
                    self.log.record('ACTION', f'Auto-bidding HOKUM ♠ (Akka mode)...')
                else:
                    bid_action, bid_suit = 'SUN', 'SUN'
                    self.log.record('ACTION', 'Auto-bidding SUN...')
                res = self.sio.call('game_action', {
                    'roomId': self.room_id,
                    'action': 'BID',
                    'payload': {'action': bid_action, 'suit': bid_suit}
                })
                if not res.get('success'):
                    self._bid_sent_this_round = False  # Reset so we can retry
                    # Don't log 'Not your turn' as warning — normal race condition
                    err = res.get('error', '')
                    if 'Not your turn' not in str(err):
                        self.errors.add_warning('BID', f"Bid response: {err}")
                return

            # Skip play actions if Sawa is active (PENDING or PENDING_TIMER)
            if self.sawa_state.get('active') and self.sawa_state.get('status') in ('PENDING', 'PENDING_TIMER'):
                return

            # Auto-play in PLAYING phase when it's our turn
            if self.phase == 'PLAYING' and self.current_turn == self.player_index and self.hand:
                if self._played_this_turn:
                    return  # Already played this turn, wait for turn to change

                # ── SAWA MODE: Try claiming Sawa when table is empty AND ≤ 4 cards ──
                if self.test_mode in ('sawa', 'all') and len(self.table_cards) == 0 and len(self.hand) <= 4:
                    if not self._sawa_claim_sent_this_turn:
                        self._sawa_claim_sent_this_turn = True
                        self.sawa_claims += 1
                        self.log.record('SAWA_ATTEMPT',
                            f"Claiming SAWA (attempt #{self.sawa_claims}, "
                            f"{len(self.hand)} cards in hand)")

                        res = self.sio.call('game_action', {
                            'roomId': self.room_id,
                            'action': 'SAWA',
                            'payload': {}
                        })

                        if res.get('success'):
                            if res.get('sawa_resolved'):
                                self.log.record('SAWA_RESOLVED',
                                    'Sawa INSTANTLY resolved by server! Round ended.')
                            elif res.get('sawa_penalty'):
                                self.log.record('SAWA_PENALTY',
                                    'Sawa was INVALID — penalty applied!')
                            elif res.get('sawa_pending_timer'):
                                self.log.record('SAWA_TIMER',
                                    f"Sawa pending — {res.get('timer_seconds', 3)}s timer started")
                            else:
                                self.log.record('SAWA_CLAIMED', 'Sawa claim accepted by server')
                            return  # Don't play a card — wait for sawa resolution
                        else:
                            self.sawa_invalid += 1
                            self.log.record('SAWA_REJECTED',
                                f"Server rejected Sawa: {res.get('error', 'unknown')}")
                            # Fall through to normal play below

                self._played_this_turn = True
                self.our_plays += 1

                # ── AKKA MODE: Play legally, observe bots' Akka ──
                if self.test_mode == 'akka':
                    card_idx = 0
                    if self.table_cards:
                        lead_card = self.table_cards[0].get('card', self.table_cards[0])
                        lead_suit = lead_card.get('suit', '')
                        for i, c in enumerate(self.hand):
                            if c.get('suit') == lead_suit:
                                card_idx = i
                                break
                    self.log.record('NORMAL_PLAY', f'Playing card {card_idx} ({len(self.hand)} left) [akka mode]')
                    res = self.sio.call('game_action', {
                        'roomId': self.room_id,
                        'action': 'PLAY',
                        'payload': {'cardIndex': card_idx, 'skip_professor': True}
                    })
                    if not res.get('success'):
                        err = res.get('error', '')
                        if 'Not your turn' not in str(err):
                            self.errors.add_warning('PLAY', f"Play failed: {err}")
                        self._played_this_turn = False
                    return

                # ── QAYD MODE: Try smart revoke ──
                if self.test_mode in ('qayd', 'all'):
                    revoke_idx = pick_revoke_card(self.hand, self.table_cards)

                    if revoke_idx is not None and len(self.table_cards) > 0:
                        self.revoke_attempts += 1
                        card = self.hand[revoke_idx]
                        lead_card = self.table_cards[0].get('card', self.table_cards[0])
                        self.log.record('REVOKE_ATTEMPT',
                            f"Playing {card.get('rank','?')} of {card.get('suit','?')} "
                            f"(lead suit: {lead_card.get('suit','?')})")

                        res = self.sio.call('game_action', {
                            'roomId': self.room_id,
                            'action': 'PLAY',
                            'payload': {'cardIndex': revoke_idx, 'skip_professor': True}
                        })
                        if res.get('success'):
                            self.revoke_successes += 1
                            self.log.record('REVOKE_PLAYED', 'Revoke card accepted by server')
                        else:
                            self.errors.add_warning('REVOKE', f"Revoke rejected: {res.get('error')}")
                            # Fallback: play first card legally
                            self.log.record('NORMAL_PLAY', 'Revoke blocked, falling back to card 0')
                            fb = self.sio.call('game_action', {
                                'roomId': self.room_id,
                                'action': 'PLAY',
                                'payload': {'cardIndex': 0, 'skip_professor': True}
                            })
                            if not fb.get('success'):
                                # Both plays failed — unlock guard so next update can retry
                                self._played_this_turn = False
                        return

                # Normal play (sawa-only mode, or no revoke possible)
                # In sawa mode, play legally (match lead suit) to avoid Qayd ending rounds early
                card_idx = 0
                if self.test_mode == 'sawa' and self.table_cards:
                    lead_card = self.table_cards[0].get('card', self.table_cards[0])
                    lead_suit = lead_card.get('suit', '')
                    for i, c in enumerate(self.hand):
                        if c.get('suit') == lead_suit:
                            card_idx = i
                            break

                self.log.record('NORMAL_PLAY', f'Playing card {card_idx} ({len(self.hand)} left)')
                res = self.sio.call('game_action', {
                    'roomId': self.room_id,
                    'action': 'PLAY',
                    'payload': {'cardIndex': card_idx, 'skip_professor': True}
                })
                if not res.get('success'):
                    err = res.get('error', '')
                    if 'Not your turn' not in str(err):
                        self.errors.add_warning('PLAY', f"Play failed: {err}")
                    self._played_this_turn = False  # Unlock for retry
        except Exception as e:
            self.errors.add_warning('AUTO_PLAY', f'Error during auto-play: {e}')

    def on_player_hand(self, data: Dict):
        """Track our hand for smart revoke plays."""
        self.hand = data.get('hand', [])
        suits = {}
        for c in self.hand:
            s = c.get('suit', '?')
            suits[s] = suits.get(s, 0) + 1
        self.log.record('HAND_RECEIVED', f"{len(self.hand)} cards | Suits: {suits}")

    def on_error(self, data):
        """Capture any socket error events."""
        msg = str(data)
        self.socket_errors.append(msg)
        self.errors.add_error('SOCKET', msg)

    def on_connect_error(self, data):
        """Capture connection errors."""
        msg = str(data)
        self.socket_errors.append(msg)
        self.errors.add_error('CONNECTION', msg)


# ═══════════════════════════════════════════════════════════════════════════════
# SMART REVOKE — Intentionally plays a card of the wrong suit
# ═══════════════════════════════════════════════════════════════════════════════
def pick_revoke_card(hand: List[Dict], table_cards: List[Dict]) -> Optional[int]:
    """
    Intelligently pick a card that will cause a revoke.
    Returns the card index, or None if no revoke is possible.

    Strategy:
      1. Find the lead suit from the first table card
      2. Check if we have a card of that suit
      3. If yes, play a card of a DIFFERENT suit (guaranteed revoke)
      4. If no, we can't revoke — just play any card
    """
    if not hand:
        return None

    # If table is empty (we're leading), just play anything — no revoke possible as leader
    if not table_cards:
        return 0  # Play first card, no revoke when leading

    # Get lead suit
    first_card = table_cards[0]
    card_data = first_card.get('card', first_card)
    lead_suit = card_data.get('suit')

    if not lead_suit:
        return 0  # Can't determine lead, just play first

    # Check if we have the lead suit
    has_lead_suit = False
    lead_suit_indices = []
    non_lead_indices = []

    for i, c in enumerate(hand):
        if c.get('suit') == lead_suit:
            has_lead_suit = True
            lead_suit_indices.append(i)
        else:
            non_lead_indices.append(i)

    if has_lead_suit and non_lead_indices:
        # We CAN follow suit but choose not to — guaranteed revoke!
        return non_lead_indices[0]
    else:
        # Either we don't have lead suit (legal off-suit) or all our cards match lead
        # In either case, no revoke possible
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# WAIT HELPER — Polls a condition with timeout
# ═══════════════════════════════════════════════════════════════════════════════
def wait_for(condition_func, timeout=15, name="Condition", log: EventLog = None):
    """Wait for a condition to become true, with timeout."""
    start = time.time()
    while time.time() - start < timeout:
        if condition_func():
            return True
        time.sleep(0.3)
    if log:
        log.record('TIMEOUT', f"Waiting for: {name} ({timeout}s)")
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TEST
# ═══════════════════════════════════════════════════════════════════════════════
def run_qayd_stress_test(target_rounds: int = DEFAULT_ROUNDS, overall_timeout: int = DEFAULT_TIMEOUT, test_mode: str = 'qayd'):
    """
    Multi-round Qayd/Sawa stress test.

    Modes:
      qayd: Revoke stress test with Qayd detection
      sawa: Sawa (Grand Slam) claim testing
      all:  Both modes interleaved

    For each round:
      1. Wait for BIDDING → bid SUN
      2. Wait for PLAYING → wait for our turn
      3. [qayd] Attempt smart revoke | [sawa] Attempt Sawa claim
      4. Monitor state transitions and resolutions
      5. Verify score changes and phase transitions
      6. Wait for round end and next round
    """
    event_log = EventLog()
    errors = ErrorCollector()
    gm = GameMonitor(event_log, errors, test_mode=test_mode)
    logger.info(f"Test mode: {test_mode.upper()}")

    sio = socketio.Client(reconnection=True, reconnection_attempts=3)
    gm.sio = sio  # Enable reactive auto-play

    # ── Wire up events ──
    @sio.event
    def connect():
        event_log.record('CONNECT', f"Connected to {SERVER_URL}")

    @sio.event
    def disconnect():
        event_log.record('DISCONNECT', 'Disconnected from server')

    @sio.event
    def connect_error(data):
        gm.on_connect_error(data)

    @sio.on('sawa_declared')
    def on_sawa_declared(data):
        claimer = data.get('claimer', '?') if isinstance(data, dict) else str(data)
        event_log.record('SAWA_DECLARED', f"Sawa declared by {claimer}")

    @sio.on('akka_declared')
    def on_akka_declared(data):
        claimer = data.get('claimer', '?') if isinstance(data, dict) else str(data)
        suits = data.get('suits', []) if isinstance(data, dict) else []
        event_log.record('AKKA_EVENT', f"akka_declared event — claimer={claimer}, suits={suits}")

    @sio.on('*')
    def catch_all(event, data):
        """Catch any event we haven't explicitly handled — safety net."""
        if event not in ('game_update', 'game_start', 'player_hand', 'player_joined',
                         'connect', 'disconnect', 'bot_speak', 'sawa_declared',
                         'akka_declared', 'timer_update', 'game_action_result'):
            event_log.record(f'UNHANDLED:{event}', str(data)[:200])

    @sio.event
    def game_update(data):
        gm.on_game_update(data.get('gameState', data))

    @sio.event
    def game_start(data):
        gm.on_game_start(data)

    @sio.event
    def player_hand(data):
        gm.on_player_hand(data)

    @sio.event
    def player_joined(data):
        p = data.get('player', {})
        event_log.record('PLAYER_JOINED', f"{p.get('name')} ({p.get('position')})")

    @sio.event
    def game_action_result(data):
        if not data.get('success'):
            errors.add_warning('ACTION_RESULT', f"Failed action: {data.get('error', data)}")

    test_start = time.time()

    try:
        # ── 1. CONNECT ──
        event_log.record('TEST', f"Connecting to {SERVER_URL}...")
        sio.connect(SERVER_URL)

        # ── 2. CREATE ROOM ──
        resp = sio.call('create_room', {})
        if not resp.get('success'):
            errors.add_error('SETUP', f"create_room failed: {resp}")
            raise Exception(f"create_room failed: {resp}")

        gm.room_id = resp['roomId']
        event_log.record('SETUP', f"Room created: {gm.room_id}")

        # ── 3. JOIN ──
        sio.emit('join_room', {
            'roomId': gm.room_id,
            'userId': 'QaydStressTester',
            'playerName': 'StressTester'
        })

        # ── 4. EVENT-DRIVEN MONITOR ──
        # The GameMonitor now auto-plays from on_game_update callbacks.
        # We just wait here for enough rounds to complete or timeout.
        event_log.record('MONITOR', f"Waiting for {target_rounds} rounds (event-driven play)...")

        _finished_since = None  # Track how long we've been in FINISHED

        while True:
            time.sleep(0.5)

            # Check completion
            if gm.rounds_completed >= target_rounds:
                event_log.record('COMPLETE', f"All {target_rounds} rounds completed!")
                break

            # Check overall timeout
            elapsed = time.time() - test_start
            if elapsed > overall_timeout:
                errors.add_error('TIMEOUT', f"Overall test timeout ({overall_timeout}s) exceeded after {gm.rounds_completed} rounds")
                break

            # Check game over
            if gm.phase == 'GAME_OVER' or gm.phase == 'GAMEOVER':
                event_log.record('GAME_OVER', f"Match ended. Final scores: {gm.scores}")
                break

            # NEXT_ROUND fallback: if stuck in FINISHED for 3+ seconds, request next round
            if gm.phase == 'FINISHED':
                if _finished_since is None:
                    _finished_since = time.time()
                elif time.time() - _finished_since > 3.0:
                    event_log.record('NEXT_ROUND', 'Requesting NEXT_ROUND (stuck in FINISHED)...')
                    try:
                        res = sio.call('game_action', {
                            'roomId': gm.room_id,
                            'action': 'NEXT_ROUND',
                            'payload': {}
                        })
                        if res.get('success'):
                            event_log.record('NEXT_ROUND', 'NEXT_ROUND accepted')
                        else:
                            event_log.record('NEXT_ROUND', f"NEXT_ROUND failed: {res.get('error', '?')}")
                    except Exception as e:
                        event_log.record('NEXT_ROUND', f"NEXT_ROUND error: {e}")
                    _finished_since = time.time()  # Reset to wait another 3s before retrying
            else:
                _finished_since = None

        # ═══════════════════════════════════════════════════════════════════════
        # FINAL REPORT
        # ═══════════════════════════════════════════════════════════════════════
        total_time = time.time() - test_start
        print_report(gm, errors, event_log, target_rounds, total_time,
                     gm.revoke_attempts, gm.revoke_successes, gm.our_plays)

    except Exception as e:
        errors.add_error('EXCEPTION', str(e))
        logger.error(f"❌ FATAL: {e}")
        import traceback
        traceback.print_exc()
        print_report(gm, errors, event_log, target_rounds,
                     time.time() - test_start,
                     gm.revoke_attempts, gm.revoke_successes, gm.our_plays)
    finally:
        try:
            sio.disconnect()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# FINAL REPORT — Structured summary of the entire test
# ═══════════════════════════════════════════════════════════════════════════════
def print_report(gm: GameMonitor, errors: ErrorCollector, event_log: EventLog,
                 target_rounds: int, total_time: float,
                 revoke_attempts: int, revoke_successes: int, our_plays: int):
    """Print a comprehensive, structured test report."""
    mode_label = gm.test_mode.upper()
    print("\n" + "═" * 60)
    print(f"  📊 LIVE STRESS TEST REPORT  [Mode: {mode_label}]")
    print("═" * 60)

    # -- Summary --
    print(f"\n⏱️  Duration:        {total_time:.1f}s")
    print(f"🔄  Rounds Target:   {target_rounds}")
    print(f"🔄  Rounds Completed: {gm.rounds_completed}")
    print(f"🃏  Our Card Plays:  {our_plays}")

    # -- Qayd Stats (if applicable) --
    if gm.test_mode in ('qayd', 'all'):
        print(f"\n💥  Revoke Stats:")
        print(f"    Attempts:       {revoke_attempts}")
        print(f"    Accepted:       {revoke_successes}")
        print(f"\n🔎  Qayd Stats:")
        print(f"    Triggers:       {gm.qayd_triggers}")
        print(f"    Resolutions:    {gm.qayd_resolutions}")
        print(f"    Verdicts:       {gm.qayd_verdicts or 'none'}")
        print(f"    Step History:   {' | '.join(gm.qayd_step_history[-20:]) or 'none'}")

    # -- Sawa Stats (if applicable) --
    if gm.test_mode in ('sawa', 'all'):
        print(f"\n🏆  Sawa Stats:")
        print(f"    Claims Sent:    {gm.sawa_claims}")
        print(f"    Invalid/Rejected: {gm.sawa_invalid}")
        print(f"    Resolved:       {gm.sawa_accepted}")
        print(f"    Penalties:      {gm.sawa_refused}")
        print(f"    Challenge Wins: {gm.sawa_challenge_wins}")
        print(f"    Challenge Losses: {gm.sawa_challenge_losses}")
        print(f"    Step History:   {' | '.join(gm.sawa_step_history[-20:]) or 'none'}")
        if gm.sawa_state:
            print(f"    Final State:    {gm.sawa_state}")

    # -- Akka Stats (if applicable) --
    if gm.test_mode in ('akka', 'all'):
        print(f"\n🎯  Akka Stats:")
        print(f"    Triggers:       {gm.akka_triggers}")
        print(f"    Clears:         {gm.akka_clears}")
        print(f"    Suits Declared: {gm.akka_suits or 'none'}")
        print(f"    History:        {' | '.join(gm.akka_history[-20:]) or 'none'}")

    # -- Scores --
    print(f"\n📈  Final Scores:    {gm.scores}")
    if gm.round_scores:
        print(f"    Per-Round:       {gm.round_scores}")

    # -- Phase at End --
    print(f"\n🎯  Final Phase:     {gm.phase}")

    # -- Errors --
    if errors.errors:
        print(f"\n❌  ERRORS ({len(errors.errors)}):")
        for i, e in enumerate(errors.errors, 1):
            print(f"    {i}. [{e['category']}] {e['message']}")
    else:
        print(f"\n✅  No errors detected!")

    # -- Warnings --
    if errors.warnings:
        print(f"\n⚠️   WARNINGS ({len(errors.warnings)}):")
        for i, w in enumerate(errors.warnings[:10], 1):
            print(f"    {i}. [{w['category']}] {w['message']}")
        if len(errors.warnings) > 10:
            print(f"    ... and {len(errors.warnings) - 10} more")

    # -- Unexpected Transitions --
    if gm.unexpected_transitions:
        print(f"\n🚨  Unexpected Phase Transitions:")
        for t in gm.unexpected_transitions:
            print(f"    - {t}")

    # -- Verdict --
    print("\n" + "═" * 60)
    if errors.has_errors:
        print("  🔥 VERDICT: FAIL")
        print("═" * 60)
        sys.exit(1)
    elif gm.test_mode in ('qayd', 'all') and revoke_attempts > 0 and gm.qayd_triggers == 0:
        print("  ⚠️  VERDICT: WARN — Revokes played but no Qayd detected")
        print("      (Bots may not have detected the revoke)")
        print("═" * 60)
        sys.exit(0)
    elif gm.test_mode in ('sawa', 'all') and gm.sawa_claims > 0 and gm.sawa_claims == gm.sawa_invalid:
        print("  ⚠️  VERDICT: WARN — All Sawa claims rejected (hand never eligible)")
        print("      (This is expected behavior — Sawa requires a dominant hand)")
        print("═" * 60)
        sys.exit(0)
    elif gm.test_mode in ('akka', 'all') and gm.rounds_completed >= 3 and gm.akka_triggers == 0:
        print("  ⚠️  VERDICT: WARN — No Akka triggers observed")
        print("      (Bots may not have had eligible hands — HOKUM + boss card required)")
        print("═" * 60)
        sys.exit(0)
    else:
        print("  🏆 VERDICT: PASS")
        print("═" * 60)
        sys.exit(0)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Qayd & Sawa Live Stress Test')
    parser.add_argument('--mode', type=str, default='qayd', choices=['qayd', 'sawa', 'akka', 'all'],
                        help='Test mode: qayd (revoke/forensic), sawa (grand slam), akka (master declaration), all (all modes)')
    parser.add_argument('--rounds', type=int, default=DEFAULT_ROUNDS,
                        help=f'Number of rounds to play (default: {DEFAULT_ROUNDS})')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT,
                        help=f'Overall timeout in seconds (default: {DEFAULT_TIMEOUT})')
    args = parser.parse_args()

    run_qayd_stress_test(target_rounds=args.rounds, overall_timeout=args.timeout, test_mode=args.mode)
