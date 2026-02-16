"""Sun mode orchestrator — delegates to extracted modules.

Lead logic stays here; follow logic in sun_follow.py,
defensive lead + signals in sun_defense.py.
"""
from ai_worker.strategies.components.base import StrategyComponent
from ai_worker.bot_context import BotContext
from ai_worker.strategies.components.signaling import (
    get_role, should_attempt_kaboot, should_break_kaboot,
    get_barqiya_response, get_ten_management_play
)
from ai_worker.strategies.components.follow_optimizer import optimize_follow
from ai_worker.strategies.components.lead_selector import select_lead
from ai_worker.strategies.components.opponent_model import model_opponents
from ai_worker.strategies.components.trick_review import review_tricks
from ai_worker.strategies.components.cooperative_play import get_cooperative_lead, get_cooperative_follow
from ai_worker.strategies.components.bid_reader import infer_from_bids
from ai_worker.strategies.components.galoss_guard import galoss_check, get_emergency_action
from ai_worker.strategies.components.sun_defense import get_defensive_lead_sun, check_ashkal_signal, check_partner_signals_sun
from ai_worker.strategies.components.sun_follow import get_sun_follow
import logging

logger = logging.getLogger(__name__)


class SunStrategy(StrategyComponent):
    """Handles all Sun mode playing logic (lead and follow)."""

    def get_decision(self, ctx: BotContext) -> dict | None:
        partner_pos = self.get_partner_pos(ctx.player_index)

        # ENDGAME SOLVER: Perfect play when ≤3 cards remain
        if len(ctx.hand) <= 3:
            endgame = self._try_endgame(ctx)
            if endgame:
                return endgame

        # ── Bayesian suit probabilities for opponents ──
        self._suit_probs: dict[str, dict[str, float]] | None = None
        try:
            if ctx.memory and hasattr(ctx.memory, 'suit_probability') and ctx.memory.suit_probability:
                opp_positions = [p.get('position') for p in ctx.raw_state.get('players', [])
                                 if p.get('position') not in (ctx.position, partner_pos)]
                self._suit_probs = {pos: ctx.memory.suit_probability.get(pos, {})
                               for pos in opp_positions if pos}
        except Exception:
            pass

        # ── TRICK REVIEW: Mid-round strategy adaptation ──
        self._trick_review = None
        try:
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            self._trick_review = review_tricks(
                my_position=ctx.position, trick_history=tricks,
                mode='SUN', trump_suit=None, we_are_buyers=(bidder_team == 'us'),
            )
            logger.debug(f"[TRICK_REVIEW] {self._trick_review['momentum']} {self._trick_review['our_tricks']}-{self._trick_review['their_tricks']} shift={self._trick_review['strategy_shift']}")
        except Exception as e:
            logger.debug(f"Trick review skipped: {e}")

        # ── OPPONENT MODEL: Threat assessment ──
        self._opp_model = None
        try:
            bid_hist = ctx.raw_state.get('bidHistory', [])
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            self._opp_model = model_opponents(
                my_position=ctx.position, bid_history=bid_hist,
                trick_history=tricks, mode='SUN', trump_suit=None,
            )
            logger.debug(f"[OPP_MODEL] danger={self._opp_model['combined_danger']} safe={self._opp_model['safe_lead_suits']} avoid={self._opp_model['avoid_lead_suits']}")
        except Exception as e:
            logger.debug(f"Opponent model skipped: {e}")

        # ── BRAIN: Cross-module orchestration ──
        try:
            from ai_worker.strategies.components.brain import consult_brain
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            master_idx = [i for i, c in enumerate(ctx.hand) if ctx.is_master_card(c)]
            table_dicts = []
            for tc in (ctx.table_cards or []):
                tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
                if isinstance(tc_card, dict):
                    table_dicts.append(tc_card)
                elif hasattr(tc_card, 'rank'):
                    table_dicts.append({"rank": tc_card.rank, "suit": tc_card.suit})
            voids: dict[str, list[str]] = {}
            for s in ['♠', '♥', '♦', '♣']:
                void_players = []
                for p in ctx.raw_state.get('players', []):
                    pos = p.get('position')
                    if pos and ctx.is_player_void(pos, s):
                        void_players.append(pos)
                if void_players:
                    voids[s] = void_players
            pi = None
            if hasattr(ctx, 'read_partner_info'):
                try:
                    pi = ctx.read_partner_info()
                except Exception:
                    pass
            brain = consult_brain(
                hand=ctx.hand, table_cards=table_dicts, mode='SUN',
                trump_suit=None, position=ctx.position,
                we_are_buyers=(bidder_team == 'us'),
                partner_winning=ctx.is_partner_winning(),
                tricks_played=len(tricks), tricks_won_by_us=our_wins,
                master_indices=master_idx, tracker_voids=voids,
                partner_info=pi,
                legal_indices=ctx.get_legal_moves(),
                opponent_info=self._opp_model,
                trick_review_info=self._trick_review,
            )
            logger.debug(f"[BRAIN] conf={brain['confidence']} modules={brain['modules_consulted']} → {brain['reasoning']}")
            if brain['recommendation'] is not None and brain['confidence'] >= 0.7:
                return {"action": "PLAY", "cardIndex": brain['recommendation'],
                        "reasoning": f"BRAIN({brain['confidence']}): {brain['reasoning']}"}
        except Exception as e:
            logger.debug(f"Brain skipped: {e}")

        # ── GALOSS GUARD: Emergency mode detection ──
        self._galoss = None
        try:
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            partner_pos = self.get_partner_pos(ctx.player_index)
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            their_wins = len(tricks) - our_wins
            our_pts = sum(t.get('points', 0) for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            their_pts = sum(t.get('points', 0) for t in tricks if t.get('winner') not in (ctx.position, partner_pos))
            self._galoss = galoss_check(
                mode='SUN', we_are_buyers=(bidder_team == 'us'),
                tricks_played=len(tricks), our_points=our_pts, their_points=their_pts,
                our_tricks=our_wins, their_tricks=their_wins,
            )
            if self._galoss['emergency_mode']:
                logger.debug(f"[GALOSS] {self._galoss['risk_level']}: {self._galoss['reasoning']}")
                legal = ctx.get_legal_moves()
                is_leading = not ctx.table_cards
                emer = get_emergency_action(
                    hand=ctx.hand, legal_indices=legal, mode='SUN',
                    trump_suit=None, we_are_buyers=(bidder_team == 'us'),
                    galoss_info=self._galoss, is_leading=is_leading,
                    partner_winning=ctx.is_partner_winning() if not is_leading else False,
                )
                if emer:
                    return {"action": "PLAY", "cardIndex": emer['card_index'],
                            "reasoning": f"Galoss/{emer['strategy']}: {emer['reasoning']}"}
        except Exception as e:
            logger.debug(f"Galoss guard skipped: {e}")

        if not ctx.table_cards:
            # Check for Ashkal Signal first
            ashkal_move = check_ashkal_signal(ctx, partner_pos)
            if ashkal_move:
                return ashkal_move
            return self._get_sun_lead(ctx)
        else:
            return get_sun_follow(ctx, self, suit_probs=self._suit_probs)

    def _get_sun_lead(self, ctx: BotContext):
        partner_pos = self.get_partner_pos(ctx.player_index)

        # DEFENSIVE LEAD: When opponents won the bid, play defensively
        bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
        if bidder_team == 'them':
            # KABOOT BREAKER: If opponents are sweeping, use masters to deny
            if should_break_kaboot(ctx):
                for i, c in enumerate(ctx.hand):
                    if ctx.is_master_card(c):
                        return {"action": "PLAY", "cardIndex": i,
                                "reasoning": "KABOOT BREAKER: Leading master to deny sweep"}

            defensive = get_defensive_lead_sun(ctx, partner_pos)
            if defensive:
                return defensive

        # ── KABOOT PURSUIT: Intelligent sweep strategy ──
        if bidder_team == 'us' and should_attempt_kaboot(ctx):
            from ai_worker.strategies.components.kaboot_pursuit import pursue_kaboot
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            master_idx = [i for i, c in enumerate(ctx.hand) if ctx.is_master_card(c)]
            kp = pursue_kaboot(
                hand=ctx.hand, mode='SUN', trump_suit=None,
                tricks_won_by_us=our_wins, tricks_played=len(tricks),
                master_cards=master_idx, partner_is_leading=False,
            )
            logger.debug(f"[KABOOT] {kp['status']}: {kp['reasoning']}")
            if kp['status'] in ('PURSUING', 'LOCKED') and kp['play_index'] is not None:
                return {"action": "PLAY", "cardIndex": kp['play_index'],
                        "reasoning": f"KABOOT {kp['status']}: {kp['reasoning']}"}

        # CHECK PARTNER SIGNALS with Barqiya timing awareness
        signal = check_partner_signals_sun(ctx, partner_pos)
        if signal:
            sig_type = signal.get('type')
            if sig_type == 'URGENT_CALL':
                legal = ctx.get_legal_moves()
                barq = get_barqiya_response(ctx, signal, legal)
                if barq:
                    return barq
            elif sig_type in ('ENCOURAGE', 'CONFIRMED_POSITIVE'):
                target_suit = signal.get('suit')
                if target_suit:
                    for i, c in enumerate(ctx.hand):
                        if c.suit == target_suit:
                            return {
                                "action": "PLAY",
                                "cardIndex": i,
                                "reasoning": f"Answering Partner's Signal ({sig_type} {target_suit})"
                            }

        # 10-MANAGEMENT: Check for Sira sequence protection
        legal = ctx.get_legal_moves()
        ten_play = get_ten_management_play(ctx, legal)
        if ten_play:
            return ten_play

        # ── COOPERATIVE LEAD: Partner-aware lead override ──
        try:
            _pi = None
            if hasattr(ctx, 'read_partner_info'):
                try: _pi = ctx.read_partner_info()
                except Exception: pass
            if _pi:
                tricks = ctx.raw_state.get('currentRoundTricks', [])
                coop = get_cooperative_lead(
                    hand=ctx.hand, partner_info=_pi, mode='SUN',
                    trump_suit=None, tricks_remaining=8 - len(tricks),
                    we_are_buyers=(bidder_team == 'us'),
                )
                if coop and coop.get('confidence', 0) >= 0.6:
                    logger.debug(f"[COOP_LEAD] {coop['strategy']}({coop['confidence']:.0%}): {coop['reasoning']}")
                    return {"action": "PLAY", "cardIndex": coop['card_index'],
                            "reasoning": f"CoopLead/{coop['strategy']}: {coop['reasoning']}"}
        except Exception as e:
            logger.debug(f"Cooperative lead skipped: {e}")

        # ── LEAD SELECTOR: Consult specialized lead module ──
        try:
            from ai_worker.strategies.components.lead_preparation import prepare_and_select_lead
            ls_decision = prepare_and_select_lead(
                ctx, mode='SUN', trump_suit=None, partner_pos=partner_pos,
                bidder_team=bidder_team, opp_model=self._opp_model,
                trick_review=self._trick_review, suit_probs=self._suit_probs,
            )
            if ls_decision:
                return ls_decision
        except Exception as e:
            logger.debug(f"Lead selector skipped: {e}")

        # Heuristic fallback scoring
        from ai_worker.strategies.components.heuristic_lead import score_sun_lead
        return score_sun_lead(ctx)
