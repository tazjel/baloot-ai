"""Hokum mode orchestrator — delegates to extracted modules.

Lead logic stays here; follow logic in hokum_follow.py,
defensive lead + signals in hokum_defense.py.
"""
from ai_worker.strategies.components.base import StrategyComponent
from ai_worker.bot_context import BotContext
from ai_worker.strategies.components.signaling import (
    get_role, should_attempt_kaboot, should_break_kaboot,
    get_barqiya_response
)
from ai_worker.strategies.components.follow_optimizer import optimize_follow
from ai_worker.strategies.components.lead_selector import select_lead
from ai_worker.strategies.components.opponent_model import model_opponents
from ai_worker.strategies.components.trick_review import review_tricks
from ai_worker.strategies.components.cooperative_play import get_cooperative_lead, get_cooperative_follow
from ai_worker.strategies.components.bid_reader import infer_from_bids
from ai_worker.strategies.components.galoss_guard import galoss_check, get_emergency_action
from ai_worker.strategies.components.hokum_defense import get_defensive_lead_hokum, check_partner_signals_hokum
from ai_worker.strategies.components.hokum_follow import get_hokum_follow
import logging

logger = logging.getLogger(__name__)


class HokumStrategy(StrategyComponent):
    """Handles all Hokum mode playing logic (lead and follow)."""

    def get_decision(self, ctx: BotContext) -> dict | None:
        # ENDGAME SOLVER: Perfect play when ≤4 cards remain
        if len(ctx.hand) <= 4:
            endgame = self._try_endgame(ctx)
            if endgame:
                return endgame

        # ── Bayesian suit probabilities for opponents ──
        partner_pos = self.get_partner_pos(ctx.player_index)
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
            partner_pos = self.get_partner_pos(ctx.player_index)
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            self._trick_review = review_tricks(
                my_position=ctx.position, trick_history=tricks,
                mode='HOKUM', trump_suit=ctx.trump, we_are_buyers=(bidder_team == 'us'),
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
                trick_history=tricks, mode='HOKUM', trump_suit=ctx.trump,
            )
            logger.debug(f"[OPP_MODEL] danger={self._opp_model['combined_danger']} safe={self._opp_model['safe_lead_suits']} avoid={self._opp_model['avoid_lead_suits']}")
        except Exception as e:
            logger.debug(f"Opponent model skipped: {e}")

        # ── BRAIN: Cross-module orchestration ──
        try:
            from ai_worker.strategies.components.brain import consult_brain
            trump = ctx.trump
            partner_pos = self.get_partner_pos(ctx.player_index)
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
                hand=ctx.hand, table_cards=table_dicts, mode='HOKUM',
                trump_suit=trump, position=ctx.position,
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
                mode='HOKUM', we_are_buyers=(bidder_team == 'us'),
                tricks_played=len(tricks), our_points=our_pts, their_points=their_pts,
                our_tricks=our_wins, their_tricks=their_wins,
            )
            if self._galoss['emergency_mode']:
                logger.debug(f"[GALOSS] {self._galoss['risk_level']}: {self._galoss['reasoning']}")
                legal = ctx.get_legal_moves()
                is_leading = not ctx.table_cards
                emer = get_emergency_action(
                    hand=ctx.hand, legal_indices=legal, mode='HOKUM',
                    trump_suit=ctx.trump, we_are_buyers=(bidder_team == 'us'),
                    galoss_info=self._galoss, is_leading=is_leading,
                    partner_winning=ctx.is_partner_winning() if not is_leading else False,
                )
                if emer:
                    return {"action": "PLAY", "cardIndex": emer['card_index'],
                            "reasoning": f"Galoss/{emer['strategy']}: {emer['reasoning']}"}
        except Exception as e:
            logger.debug(f"Galoss guard skipped: {e}")

        if not ctx.table_cards:
            return self._get_hokum_lead(ctx)
        else:
            return get_hokum_follow(ctx, self, suit_probs=self._suit_probs)

    def _get_hokum_lead(self, ctx: BotContext):
        trump = ctx.trump
        partner_pos = self.get_partner_pos(ctx.player_index)

        # Determine if we (or partner) bought the project.
        bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'

        # DEFENSIVE LEAD: When opponents won the bid, switch to defensive strategy
        if bidder_team == 'them':
            # KABOOT BREAKER: If opponents are sweeping, prioritize winning 1 trick
            if should_break_kaboot(ctx):
                for i, c in enumerate(ctx.hand):
                    if ctx.is_master_card(c):
                        return {"action": "PLAY", "cardIndex": i,
                                "reasoning": "KABOOT BREAKER: Leading master to deny sweep"}

            defensive = get_defensive_lead_hokum(ctx, partner_pos)
            if defensive:
                return defensive

        # ── KABOOT PURSUIT: Intelligent sweep strategy ──
        if bidder_team == 'us' and should_attempt_kaboot(ctx):
            from ai_worker.strategies.components.kaboot_pursuit import pursue_kaboot
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            master_idx = [i for i, c in enumerate(ctx.hand) if ctx.is_master_card(c)]
            kp = pursue_kaboot(
                hand=ctx.hand, mode='HOKUM', trump_suit=trump,
                tricks_won_by_us=our_wins, tricks_played=len(tricks),
                master_cards=master_idx, partner_is_leading=False,
            )
            logger.debug(f"[KABOOT] {kp['status']}: {kp['reasoning']}")
            if kp['status'] in ('PURSUING', 'LOCKED') and kp['play_index'] is not None:
                return {"action": "PLAY", "cardIndex": kp['play_index'],
                        "reasoning": f"KABOOT {kp['status']}: {kp['reasoning']}"}

        # CHECK PARTNER SIGNALS (Hokum-specific)
        signal = check_partner_signals_hokum(ctx, partner_pos)
        if signal:
            if signal.get('type') == 'URGENT_CALL':
                legal = ctx.get_legal_moves()
                barq = get_barqiya_response(ctx, signal, legal)
                if barq:
                    return barq
            elif signal.get('type') in ('ENCOURAGE', 'CONFIRMED_POSITIVE'):
                target_suit = signal.get('suit')
                if target_suit:
                    for i, c in enumerate(ctx.hand):
                        if c.suit == target_suit:
                            return {"action": "PLAY", "cardIndex": i,
                                    "reasoning": f"Answering partner signal: Lead {target_suit}"}

        # ── COOPERATIVE LEAD: Partner-aware lead override ──
        try:
            _pi = None
            if hasattr(ctx, 'read_partner_info'):
                try: _pi = ctx.read_partner_info()
                except Exception: pass
            if _pi:
                tricks = ctx.raw_state.get('currentRoundTricks', [])
                coop = get_cooperative_lead(
                    hand=ctx.hand, partner_info=_pi, mode='HOKUM',
                    trump_suit=trump, tricks_remaining=8 - len(tricks),
                    we_are_buyers=(bidder_team == 'us'),
                )
                if coop and coop.get('confidence', 0) >= 0.6:
                    logger.debug(f"[COOP_LEAD] {coop['strategy']}({coop['confidence']:.0%}): {coop['reasoning']}")
                    return {"action": "PLAY", "cardIndex": coop['card_index'],
                            "reasoning": f"CoopLead/{coop['strategy']}: {coop['reasoning']}"}
        except Exception as e:
            logger.debug(f"Cooperative lead skipped: {e}")

        # ── TRUMP MANAGEMENT ENGINE ──
        from ai_worker.strategies.components.trump_manager import manage_trumps

        my_trump_count = sum(1 for c in ctx.hand if c.suit == trump)

        # Estimate enemy trumps using Bayesian probabilities + CardTracker
        enemy_void_suits = []
        partner_void_suits = []
        partner_trump_prob = 0.0
        for p in ctx.raw_state.get('players', []):
            pos = p.get('position')
            if p.get('team') != ctx.team:
                for s in ['♠', '♥', '♦', '♣']:
                    if s != trump and ctx.is_player_void(pos, s):
                        enemy_void_suits.append(s)
            elif pos == partner_pos:
                partner_trump_prob = ctx.memory.get_suit_probability(pos, trump)
                for s in ['♠', '♥', '♦', '♣']:
                    if s != trump and ctx.is_player_void(pos, s):
                        partner_void_suits.append(s)
        total_unseen_trumps = ctx.tracker.count_remaining_trump(trump)
        partner_trump_est = round(partner_trump_prob * min(total_unseen_trumps, 3))
        remaining_enemy_trumps = max(0, total_unseen_trumps - partner_trump_est)

        tricks = ctx.raw_state.get('currentRoundTricks', [])
        tplan = manage_trumps(
            hand=ctx.hand, trump_suit=trump, my_trumps=my_trump_count,
            enemy_trumps_estimate=remaining_enemy_trumps,
            partner_trumps_estimate=partner_trump_est,
            tricks_played=len(tricks), we_are_buyers=(bidder_team == 'us'),
            partner_void_suits=partner_void_suits,
            enemy_void_suits=enemy_void_suits,
        )
        logger.debug(f"[TRUMP] {tplan['action']} phase={tplan.get('phase', '?')}: {tplan['reasoning']}")
        should_open_trump = tplan['lead_trump']
        ruffable_suits = set(enemy_void_suits)

        # ── TRUMP TIMING: CASH_SIDES phase override ──
        if tplan.get('phase') == 'CASH_SIDES':
            cash_suits = tplan.get('side_winner_suits', [])
            for cs in cash_suits:
                for i, c in enumerate(ctx.hand):
                    if c.suit == cs and c.rank == 'A':
                        return {"action": "PLAY", "cardIndex": i,
                                "reasoning": f"Trump Timing Phase 2: Cash {c.rank}{cs} before enemy ruffs"}
            for cs in cash_suits:
                for i, c in enumerate(ctx.hand):
                    if c.suit == cs and c.rank == 'K':
                        return {"action": "PLAY", "cardIndex": i,
                                "reasoning": f"Trump Timing Phase 2: Cash {c.rank}{cs} (protected by Ace lead)"}
            logger.debug("[TRUMP] CASH_SIDES phase but no side winners found — falling through")

        # ── LEAD SELECTOR: Consult specialized lead module ──
        try:
            from ai_worker.strategies.components.lead_preparation import prepare_and_select_lead
            ls_decision = prepare_and_select_lead(
                ctx, mode='HOKUM', trump_suit=trump, partner_pos=partner_pos,
                bidder_team=bidder_team, opp_model=self._opp_model,
                trick_review=self._trick_review, suit_probs=self._suit_probs,
                trump_info=tplan,
            )
            if ls_decision:
                return ls_decision
        except Exception as e:
            logger.debug(f"Lead selector skipped: {e}")

        # Heuristic fallback scoring
        from ai_worker.strategies.components.heuristic_lead import score_hokum_lead
        return score_hokum_lead(ctx, trump, should_open_trump, remaining_enemy_trumps, ruffable_suits)
