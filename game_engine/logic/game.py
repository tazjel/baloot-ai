"""
game_engine/logic/game.py — Refactored Game Controller (v2)
=============================================================

454 lines. Architecture:
  - State:      self.state (GameState Pydantic model) — single source of truth
  - Properties: StateBridgeMixin — legacy aliases (game.phase -> game.state.phase)
  - Phases:     self.phases[phase].handle_action() — delegated logic
  - Auto-play:  AutoPilot.execute() — extracted bot/timeout logic
  - Tracking:   self.graveyard — O(1) played-card lookups
  - Events:     ActionResult + GameEvent — typed results

Persistence: redis.set(key, game.state.model_dump_json())
"""

from __future__ import annotations
import random, time, copy, logging
from typing import Dict, List, Optional, Any
from functools import wraps

from game_engine.models.constants import GamePhase
from game_engine.models.deck import Deck
from game_engine.models.player import Player
from game_engine.logic.utils import sort_hand
from game_engine.core.state import GameState, BidState, AkkaState
from game_engine.core.graveyard import Graveyard
from game_engine.core.models import ActionResult, EventType

from .state_bridge import StateBridgeMixin
from .timer_manager import TimerManager
from .trick_manager import TrickManager
from .scoring_engine import ScoringEngine
from .project_manager import ProjectManager
from .akka_manager import AkkaManager
from .sawa_manager import SawaManager
from .qayd_engine import QaydEngine
from .phases.challenge_phase import ChallengePhase
from .phases.bidding_phase import BiddingPhase as BiddingLogic
from .phases.playing_phase import PlayingPhase as PlayingLogic
from .autopilot import AutoPilot

from server.logging_utils import log_event, logger


def requires_unlocked(func):
    @wraps(func)
    def wrapper(self, *a, **kw):
        if self.state.isLocked:
            return {'success': False, 'error': 'Game is locked'}
        return func(self, *a, **kw)
    return wrapper


class Game(StateBridgeMixin):
    """Lightweight game controller. All mutable state in self.state."""

    def __init__(self, room_id: str):
        self.state = GameState(roomId=room_id)
        self._floor_card_obj = None

        # Transient (not serialized into state)
        self.deck = Deck()
        self.players: List[Player] = []
        self.table_cards: List[Dict] = []
        self.timer = TimerManager(5)
        self.timer_paused = False
        self.turn_duration = 30
        self.bidding_engine = None

        # Managers
        self.graveyard = Graveyard()
        self.trick_manager = TrickManager(self)
        self.scoring_engine = ScoringEngine(self)
        self.project_manager = ProjectManager(self)
        self.akka_manager = AkkaManager(self)
        self.sawa_manager = SawaManager(self)
        self.challenge_phase = ChallengePhase(self)
        self.qayd_engine = QaydEngine(self)
        self.qayd_engine.reset()
        self.qayd_state = self.qayd_engine.state

        # Phase Handlers
        self.phases = {
            GamePhase.BIDDING.value:   BiddingLogic(self),
            GamePhase.PLAYING.value:   PlayingLogic(self),
            GamePhase.CHALLENGE.value: self.challenge_phase,
        }

        # Recorder (optional)
        try:
            from server.common import redis_client
            from game_engine.core.recorder import TimelineRecorder
            self.recorder = TimelineRecorder(redis_client)
        except Exception:
            self.recorder = None
        self._record("INIT")

    # ═══════════════════════════════════════════════════════════════════
    #  LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════

    def add_player(self, id, name, avatar=None):
        for p in self.players:
            if p.id == id:
                p.name = name
                if avatar: p.avatar = avatar
                return p
        if len(self.players) >= 4: return None
        p = Player(id, name, len(self.players), self, avatar=avatar)
        self.players.append(p)
        return p

    def start_game(self) -> bool:
        if len(self.players) < 4: return False
        self.reset_round_state()
        self.dealer_index = random.randint(0, 3)
        self.deal_initial_cards()
        self.phase = GamePhase.BIDDING.value
        from .bidding_engine import BiddingEngine
        self.bidding_engine = BiddingEngine(
            dealer_index=self.dealer_index, floor_card=self._floor_card_obj,
            players=self.players, match_scores=self.match_scores,
        )
        self.current_turn = self.bidding_engine.current_turn
        self.reset_timer()
        return True

    def reset_round_state(self):
        self.deck = Deck()
        for p in self.players:
            p.hand, p.captured_cards, p.action_text = [], [], ''
        self.table_cards = []
        self._floor_card_obj = None
        self.state.reset_round()
        self.graveyard.reset()
        self.qayd_engine.reset()
        self.qayd_state = self.qayd_engine.state
        # akka_state and sawa_state are reset by state.reset_round() automatically
        self.reset_timer()

    def deal_initial_cards(self):
        for p in self.players:
            p.hand.extend(self.deck.deal(5))
        val = self.deck.deal(1)
        if val: self.floor_card = val[0]

    def complete_deal(self, bidder_index):
        bidder = self.players[bidder_index]
        if self._floor_card_obj:
            bidder.hand.append(self._floor_card_obj)
            self.floor_card = None
        bidder.hand.extend(self.deck.deal(2))
        for p in self.players:
            if p.index != bidder_index:
                p.hand.extend(self.deck.deal(3))
        for p in self.players:
            p.hand = sort_hand(p.hand, self.game_mode, self.trump_suit)
            p.action_text = ""
            self.initial_hands[p.position] = [c.to_dict() for c in p.hand]
        self.phase = GamePhase.PLAYING.value
        self.current_turn = (self.dealer_index + 1) % 4
        self.reset_timer()

        # Auto-declare projects for all bots at start of play
        # so their labels show immediately during trick 1
        if hasattr(self, 'project_manager'):
            self.project_manager.auto_declare_bot_projects()

    # ═══════════════════════════════════════════════════════════════════
    #  ACTION DELEGATION
    # ═══════════════════════════════════════════════════════════════════

    @requires_unlocked
    def handle_bid(self, player_index, action, suit=None, reasoning=None):
        if self.phase != GamePhase.BIDDING.value:
            return {'success': False, 'error': f"Not in BIDDING. Current: {self.phase}"}
        return self.phases[GamePhase.BIDDING.value].handle_bid(player_index, action, suit, reasoning)

    @requires_unlocked
    def play_card(self, player_index, card_idx, metadata=None):
        if self.phase != GamePhase.PLAYING.value:
            return {'success': False, 'error': f"Not in PLAYING. Current: {self.phase}"}
        result = self.phases[GamePhase.PLAYING.value].play_card(player_index, card_idx, metadata)
        if result.get('success') and self.table_cards:
            self.graveyard.add(self.table_cards[-1])
        return result

    def handle_double(self, player_index):
        if not self.bid.get('type'): return {"error": "No bid to double"}
        bidder_pos, doubler_pos = self.bid['bidder'], self.players[player_index].position
        same = (bidder_pos in ('Bottom','Top') and doubler_pos in ('Bottom','Top')) or \
               (bidder_pos in ('Right','Left') and doubler_pos in ('Right','Left'))
        if same:                      return {"error": "Cannot double your partner"}
        if self.doubling_level >= 2:  return {"error": "Already doubled"}
        self.doubling_level = 2
        b = self.bid; b['doubled'] = True; self.bid = b
        self.is_locked = True
        return {"success": True}

    # ── Sub-system pass-throughs ─────────────────────────────────────

    def handle_declare_project(self, pi, t):  return self.project_manager.handle_declare_project(pi, t)
    def resolve_declarations(self):           return self.project_manager.resolve_declarations()
    def check_akka_eligibility(self, pi):     return self.akka_manager.check_akka_eligibility(pi)
    def handle_akka(self, pi):                return self.akka_manager.handle_akka(pi)

    def handle_sawa(self, pi):
        return self.trick_manager.handle_sawa(pi)

    def handle_sawa_timeout(self):
        return self.trick_manager.handle_sawa_timeout()

    def handle_sawa_qayd(self, pi):
        return self.trick_manager.handle_sawa_qayd(pi)

    def is_valid_move(self, card, hand):       return self.trick_manager.is_valid_move(card, hand)

    def resolve_trick(self):
        result = self.trick_manager.resolve_trick()
        if self.round_history:
            self.graveyard.commit_trick(self.round_history[-1].get('cards', []))
        # Clear Akka after trick resolves — it’s a one-trick announcement
        self.state.akkaState = AkkaState()
        return result

    # ── Qayd delegation ──────────────────────────────────────────────

    def handle_qayd_trigger(self, pi):              return self.qayd_engine.trigger(pi)
    def handle_qayd_menu_select(self, pi, o):       return self.qayd_engine.select_menu_option(o)
    def handle_qayd_violation_select(self, pi, v):  return self.qayd_engine.select_violation(v)
    def handle_qayd_select_crime(self, pi, d):      return self.qayd_engine.select_crime_card(d)
    def handle_qayd_select_proof(self, pi, d):      return self.qayd_engine.select_proof_card(d)
    def handle_qayd_confirm(self):                  return self.qayd_engine.confirm()
    def handle_qayd(self, pi, reason=None):         return self.handle_qayd_trigger(pi)
    def handle_qayd_accusation(self, pi, acc=None):
        return self.qayd_engine.trigger(pi) if not acc else self.qayd_engine.handle_bot_accusation(pi, acc)
    def handle_qayd_cancel(self):
        r = self.qayd_engine.cancel()
        if r.get('success') and self.phase == GamePhase.FINISHED.value:
            r['trigger_next_round'] = True
        return r

    def process_accusation(self, pi, d): return self.qayd_engine.handle_bot_accusation(pi, d)

    # ═══════════════════════════════════════════════════════════════════
    #  SCORING / ROUND END
    # ═══════════════════════════════════════════════════════════════════

    def end_round(self, skip_scoring=False):
        self._record("ROUND_END")
        if not skip_scoring:
            rr, su, st = self.scoring_engine.calculate_final_scores()
            self.past_round_results.append(rr)
            self.match_scores['us'] += su
            self.match_scores['them'] += st
            snap = self._build_round_snapshot(rr)
            self.full_match_history.append(snap)
            try:
                from ai_worker.agent import bot_agent
                bot_agent.capture_round_data(snap)
            except Exception: pass

        self.dealer_index = (self.dealer_index + 1) % 4
        if self.match_scores['us'] >= 152 or self.match_scores['them'] >= 152:
            self.phase = GamePhase.GAMEOVER.value
            try:
                from server.services.archiver import archive_match
                archive_match(self)
            except Exception: pass
        else:
            self.phase = GamePhase.FINISHED.value
        self.sawa_failed_khasara = False
        self.reset_timer()

    def apply_qayd_penalty(self, loser_team, winner_team):
        penalty = self.qayd_state.get('penalty_points', 26 if 'SUN' in str(self.game_mode).upper() else 16)
        proj_pts = sum(p.get('score',0) for projs in self.declarations.values() for p in projs)
        total = penalty + proj_pts
        self.match_scores[winner_team] += total
        rr = self._build_qayd_round_result(winner_team, total)
        self.past_round_results.append(rr)
        self.full_match_history.append(self._build_round_snapshot(rr))
        self.dealer_index = (self.dealer_index + 1) % 4
        self.phase = GamePhase.GAMEOVER.value if (self.match_scores['us'] >= 152 or self.match_scores['them'] >= 152) else GamePhase.FINISHED.value

    # ═══════════════════════════════════════════════════════════════════
    #  TIMEOUT — Delegates to AutoPilot
    # ═══════════════════════════════════════════════════════════════════

    # @requires_unlocked  <-- Removed to clear deadlock
    def check_timeout(self):
        is_chal = self.phase == GamePhase.CHALLENGE.value or self.qayd_state.get('active')
        if (not self.timer.active or self.timer_paused) and not is_chal: return None
        if self.phase in (GamePhase.FINISHED.value, GamePhase.GAMEOVER.value):
            self.timer.stop(); return None
        if is_chal:
            qr = self.qayd_engine.check_timeout()
            if qr: return qr
        if not self.timer.is_expired(): return None

        if self.phase == GamePhase.BIDDING.value:
            res = self.handle_bid(self.current_turn, "PASS")
        elif self.phase == GamePhase.PLAYING.value:
            r = AutoPilot.execute(self, self.current_turn)
            res = r.to_legacy_dict() if isinstance(r, ActionResult) else r
        elif is_chal:
            res = self._handle_challenge_timeout()
        else:
            res = None

        if res and not res.get('success'):
            if is_chal: res = self.handle_qayd_cancel()
            elif self.phase == GamePhase.BIDDING.value: res = self.handle_bid(self.current_turn, "PASS")
            self.reset_timer(1.0)
        if self.timer.is_expired(): self.reset_timer()
        return res

    def auto_play_card(self, player_index):
        """Legacy entry point -> AutoPilot."""
        r = AutoPilot.execute(self, player_index)
        return r.to_legacy_dict() if isinstance(r, ActionResult) else r

    # ═══════════════════════════════════════════════════════════════════
    #  STATE EXPORT (for frontend)
    # ═══════════════════════════════════════════════════════════════════

    def get_game_state(self) -> Dict[str, Any]:
        return {
            "roomId": self.room_id, "phase": self.phase,
            "biddingPhase": self.bidding_engine.phase.name if self.bidding_engine else None,
            "players": [p.to_dict() for p in self.players],
            "tableCards": [
                {"playerId": tc['playerId'], "card": tc['card'].to_dict(), "playedBy": tc['playedBy'], "metadata": tc.get('metadata')}
                for tc in self.table_cards],
            "currentTurnIndex": self.current_turn,
            "gameMode": self.game_mode, "trumpSuit": self.trump_suit,
            "bid": self.bid, "teamScores": self.team_scores, "matchScores": self.match_scores,
            "analytics": {"winProbability": self.win_probability_history, "blunders": self.blunders},
            "floorCard": self._floor_card_obj.to_dict() if self._floor_card_obj else None,
            "dealerIndex": self.dealer_index, "biddingRound": self.state.biddingRound,
            "declarations": {
                pos: [{**p, 'cards': [c.to_dict() if hasattr(c,'to_dict') else c for c in p.get('cards',[])]} for p in projs]
                for pos, projs in self.declarations.items()},
            "timer": {"remaining": self.timer.get_time_remaining(), "duration": self.timer.duration,
                      "elapsed": self.timer.get_time_elapsed(), "active": self.timer.active},
            "isProjectRevealing": self.is_project_revealing,
            "trickCount": len(self.round_history),
            "doublingLevel": self.doubling_level, "isLocked": self.is_locked,
            "strictMode": self.strictMode, "dealingPhase": self.dealing_phase,
            "lastTrick": self.last_trick, "roundHistory": self.past_round_results,
            "currentRoundTricks": [
                {"winner": t.get("winner"), "points": t.get("points"),
                 "cards": self._ser_tc(t.get("cards",[])),
                 "playedBy": t.get("playedBy"), "metadata": t.get("metadata")}
                for t in self.round_history],
            "sawaState": self.state.sawaState.model_dump(),
            "qaydState": self.qayd_engine.get_frontend_state(),
            "challengeActive": self.phase == GamePhase.CHALLENGE.value,
            "timerStartTime": getattr(self.timer,'start_time',0),
            "turnDuration": self.turn_duration, "serverTime": time.time(),
            "akkaState": self.state.akkaState.model_dump() if self.state.akkaState.active else None,
            "gameId": self.room_id, "settings": self.state.settings,
            "resolvedCrimes": self.state.resolved_crimes,
        }

    # ═══════════════════════════════════════════════════════════════════
    #  INTERNAL HELPERS
    # ═══════════════════════════════════════════════════════════════════

    def _sync_bid_state(self):
        if not self.bidding_engine: return
        c = self.bidding_engine.contract
        tb = self.bidding_engine.tentative_bid
        if c.type:
            self.bid = {"type": c.type.value, "bidder": self.players[c.bidder_idx].position,
                "doubled": c.level >= 2, "suit": c.suit, "level": c.level,
                "variant": c.variant, "isAshkal": c.is_ashkal, "isTentative": False}
            self.game_mode, self.trump_suit, self.doubling_level = c.type.value, c.suit, c.level
        elif tb:
            self.bid = {"type": tb['type'], "bidder": self.players[tb['bidder']].position,
                "doubled": False, "suit": tb['suit'], "level": 1,
                "variant": None, "isAshkal": tb['type'] == 'ASHKAL', "isTentative": True}
        else:
            self.bid = {"type": None, "bidder": None, "doubled": False}

    def calculate_win_probability(self):
        ru = sum(t['points'] for t in self.round_history if t['winner'] in ('Bottom','Top'))
        rt = sum(t['points'] for t in self.round_history if t['winner'] in ('Right','Left'))
        d = (self.match_scores['us']+ru) - (self.match_scores['them']+rt)
        return max(0.0, min(1.0, 0.5 + (d/152.0)*0.5))

    def increment_blunder(self, pi):
        pos = self.players[pi].position
        self.blunders[pos] = self.blunders.get(pos, 0) + 1

    def reset_timer(self, duration=None):
        self.timer.reset(duration); self.timer_paused = False

    def pause_timer(self):  self.timer_paused = True;  self.timer.pause()
    def resume_timer(self): self.timer_paused = False; self.timer.resume()

    @staticmethod
    def _ser_tc(cards):
        out = []
        for c in cards:
            if isinstance(c, dict):
                if 'card' in c:
                    i = c['card']
                    out.append({**c, 'card': i.to_dict() if hasattr(i,'to_dict') else i})
                else: out.append(c)
            elif hasattr(c, 'to_dict'): out.append(c.to_dict())
            else: out.append(c)
        return out

    def _record(self, ev, details=""):
        if self.recorder:
            try: self.recorder.record_state(self.state, ev, details)
            except Exception: pass

    def _build_round_snapshot(self, rr):
        sd = {pos: [{**p, 'cards': [c.to_dict() if hasattr(c,'to_dict') else c for c in p.get('cards',[])]} for p in projs]
              for pos, projs in self.declarations.items()}
        return {'roundNumber': len(self.past_round_results), 'bid': copy.deepcopy(self.bid),
                'scores': copy.deepcopy(rr), 'tricks': copy.deepcopy(self.round_history),
                'dealerIndex': self.dealer_index,
                'floorCard': self._floor_card_obj.to_dict() if self._floor_card_obj else None,
                'declarations': sd, 'initialHands': self.initial_hands}

    def _build_qayd_round_result(self, winner, total):
        z = {'result': 0, 'aklat': 0, 'ardh': 0, 'projects': [], 'abnat': 0, 'isKaboot': True}
        return {'roundNumber': len(self.past_round_results)+1, 'qayd': True, 'winner': winner,
                'us': {**z, 'result': total} if winner == 'us' else z,
                'them': {**z, 'result': total} if winner == 'them' else z}

    def _handle_challenge_timeout(self):
        qr = self.qayd_engine.check_timeout()
        if qr: return qr
        rp = self.qayd_state.get('reporter')
        ri = next((p.index for p in self.players if p.position == rp), -1)
        if ri != -1: return AutoPilot.execute(self, ri)
        self.handle_qayd_cancel()
        return {'success': True, 'action': 'ZOMBIE_REPAIR'}

    # === JSON SERIALIZATION ===

    def to_json(self) -> dict:
        """Serialize the full game to a JSON-safe dict."""
        from .game_serializer import serialize_game
        return serialize_game(self)

    @classmethod
    def from_json(cls, data: dict) -> 'Game':
        """Reconstruct a full Game object from a JSON dict."""
        from .game_serializer import deserialize_game
        return deserialize_game(data)

