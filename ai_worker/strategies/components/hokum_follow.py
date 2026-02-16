"""Hokum follow-suit logic.

Extracted from HokumStrategy for file size reduction.
Handles all follow decisions when table_cards is non-empty in HOKUM mode.
"""
from __future__ import annotations
import logging
from ai_worker.bot_context import BotContext
from game_engine.models.constants import POINT_VALUES_HOKUM, ORDER_HOKUM
from ai_worker.strategies.components.follow_optimizer import optimize_follow
from ai_worker.strategies.components.cooperative_play import get_cooperative_follow

logger = logging.getLogger(__name__)


def get_hokum_follow(ctx: BotContext, strategy, suit_probs=None) -> dict:
    """Full Hokum follow-suit decision pipeline.

    @param ctx: BotContext
    @param strategy: The HokumStrategy instance (for base class helpers)
    @param suit_probs: Optional Bayesian suit probabilities dict
    @returns Play decision dict
    """
    lead_suit = ctx.lead_suit
    winning_card = ctx.winning_card
    winner_pos = ctx.winner_pos
    trump = ctx.trump

    follows = [i for i, c in enumerate(ctx.hand) if c.suit == lead_suit]

    # SEAT-AWARE POSITIONAL PLAY
    seat = len(ctx.table_cards) + 1  # 2nd, 3rd, or 4th seat

    # POINT DENSITY: Evaluate trick's point value
    from ai_worker.strategies.components.point_density import evaluate_trick_value
    _table_dicts = []
    for tc in ctx.table_cards:
        tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
        if isinstance(tc_card, dict):
            _table_dicts.append(tc_card)
        elif hasattr(tc_card, 'rank'):
            _table_dicts.append({"rank": tc_card.rank, "suit": tc_card.suit})
    _trick_ev = evaluate_trick_value(_table_dicts, 'HOKUM')
    trick_points = _trick_ev['current_points']
    logger.debug(f"[POINTS] {_trick_ev['density']} ({trick_points}pts, {_trick_ev['point_cards_on_table']} pt-cards)")

    # ── COOPERATIVE FOLLOW: Partner-aware follow override ──
    try:
        _pi = None
        if hasattr(ctx, 'read_partner_info'):
            try: _pi = ctx.read_partner_info()
            except Exception: pass
        if _pi:
            partner_pos = strategy.get_partner_pos(ctx.player_index)
            is_partner_winning = (winner_pos == partner_pos)
            coop_f = get_cooperative_follow(
                hand=ctx.hand, legal_indices=follows if follows else list(range(len(ctx.hand))),
                partner_info=_pi, led_suit=lead_suit, mode='HOKUM',
                trump_suit=trump, partner_winning=is_partner_winning,
                trick_points=trick_points,
            )
            if coop_f and coop_f.get('confidence', 0) >= 0.6:
                logger.debug(f"[COOP_FOLLOW] {coop_f['tactic']}({coop_f['confidence']:.0%}): {coop_f['reasoning']}")
                return {"action": "PLAY", "cardIndex": coop_f['card_index'],
                        "reasoning": f"CoopFollow/{coop_f['tactic']}: {coop_f['reasoning']}"}
    except Exception as e:
        logger.debug(f"Cooperative follow skipped: {e}")

    # 1. Void Clause — seat-aware trumping decision
    if not follows:
        partner_pos = strategy.get_partner_pos(ctx.player_index)
        is_partner_winning = (winner_pos == partner_pos)

        try:
            from ai_worker.strategies.components.void_trumping import decide_void_trump
            trump_decision = decide_void_trump(
                ctx, trump, winning_card, seat, trick_points, is_partner_winning)
            if trump_decision:
                return trump_decision
        except Exception as e:
            logger.debug(f"Void trumping skipped: {e}")

        return strategy.get_trash_card(ctx)

    # 2. Follow Suit Clause
    partner_pos = strategy.get_partner_pos(ctx.player_index)
    is_partner_winning = (winner_pos == partner_pos)

    if is_partner_winning:
        # ── FOLLOW OPTIMIZER: Partner winning path ──
        fo_result = _try_follow_optimizer(
            ctx, follows, lead_suit, trump, seat, trick_points,
            partner_pos, True, suit_probs, strategy)
        if fo_result:
            return fo_result
        best_idx = strategy.find_highest_point_card(ctx, follows, POINT_VALUES_HOKUM)
        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Partner Winning - Feeding"}
    else:
        if winning_card.suit == trump and lead_suit != trump:
            best_idx = strategy.find_lowest_point_card(ctx, follows, POINT_VALUES_HOKUM)
            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Enemy Trumping - Point Protection"}

        winners = []
        for idx in follows:
            c = ctx.hand[idx]
            if ctx._compare_ranks(c.rank, winning_card.rank, 'HOKUM'):
                winners.append(idx)

        if winners:
            # ── FOLLOW OPTIMIZER: Competitive path ──
            fo_result = _try_follow_optimizer(
                ctx, follows, lead_suit, trump, seat, trick_points,
                partner_pos, False, suit_probs, strategy)
            if fo_result:
                return fo_result
            if seat == 4:
                # 4TH SEAT: Guaranteed win — finesse with lowest winner
                best_idx = strategy.find_lowest_rank_card(ctx, winners, ORDER_HOKUM)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "4th Seat Finesse"}
            elif seat == 3:
                # 3RD SEAT: Aggressive — use stronger card for important tricks
                if trick_points >= 10:
                    best_idx = strategy.find_best_winner(ctx, winners, ORDER_HOKUM)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Securing Big Trick"}
                else:
                    best_idx = strategy.find_lowest_rank_card(ctx, winners, ORDER_HOKUM)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Economy Win"}
            else:
                # 2ND SEAT: Conservative — only commit masters or high-stakes
                master_winners = [i for i in winners if ctx.is_master_card(ctx.hand[i])]
                if master_winners:
                    best_idx = strategy.find_lowest_rank_card(ctx, master_winners, ORDER_HOKUM)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Playing Master"}
                elif trick_points >= 15:
                    best_idx = strategy.find_lowest_rank_card(ctx, winners, ORDER_HOKUM)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: High-Stakes Commit"}
                else:
                    best_idx = strategy.find_lowest_point_card(ctx, follows, POINT_VALUES_HOKUM)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Ducking for Partner"}
        else:
            best_idx = strategy.find_lowest_point_card(ctx, follows, POINT_VALUES_HOKUM)
            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Ducking (Point Protection)"}


def _try_follow_optimizer(ctx, follows, lead_suit, trump, seat, trick_points,
                          partner_pos, partner_winning, suit_probs, strategy) -> dict | None:
    """Attempt follow_optimizer call, return result or None."""
    try:
        bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
        _fo_table = []
        for tc in ctx.table_cards:
            tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
            if isinstance(tc_card, dict):
                _fo_table.append({"rank": tc_card.get('rank', ''), "suit": tc_card.get('suit', ''), "position": tc.get('playedBy', '')})
            elif hasattr(tc_card, 'rank'):
                _fo_table.append({"rank": tc_card.rank, "suit": tc_card.suit, "position": tc.get('playedBy', '')})
        _partner_card_idx = None
        for ti, tc in enumerate(ctx.table_cards):
            if tc.get('playedBy') == partner_pos:
                _partner_card_idx = ti
                break
        tricks = ctx.raw_state.get('currentRoundTricks', [])
        fo_result = optimize_follow(
            hand=ctx.hand, legal_indices=follows, table_cards=_fo_table,
            led_suit=lead_suit, mode='HOKUM', trump_suit=trump, seat=seat,
            partner_winning=partner_winning, partner_card_index=_partner_card_idx,
            trick_points=trick_points, tricks_remaining=8 - len(tricks),
            we_are_buyers=(bidder_team == 'us'),
            suit_probs=suit_probs,
        )
        if fo_result and fo_result.get('confidence', 0) >= 0.6:
            logger.debug(f"[FOLLOW_OPT] {fo_result['tactic']}({fo_result['confidence']:.0%}): {fo_result['reasoning']}")
            return {"action": "PLAY", "cardIndex": fo_result['card_index'],
                    "reasoning": f"FollowOpt/{fo_result['tactic']}: {fo_result['reasoning']}"}
    except Exception as e:
        logger.debug(f"Follow optimizer skipped: {e}")
    return None
