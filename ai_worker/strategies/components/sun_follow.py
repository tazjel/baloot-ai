"""Sun follow-suit logic.

Extracted from SunStrategy for file size reduction.
Handles all follow decisions when table_cards is non-empty in SUN mode.
"""
from __future__ import annotations
import logging
from ai_worker.bot_context import BotContext
from game_engine.models.constants import POINT_VALUES_SUN, ORDER_SUN
from ai_worker.strategies.components.follow_optimizer import optimize_follow
from ai_worker.strategies.components.cooperative_play import get_cooperative_follow

logger = logging.getLogger(__name__)


def get_sun_follow(ctx: BotContext, strategy, suit_probs=None) -> dict:
    """Full Sun follow-suit decision pipeline.

    @param ctx: BotContext
    @param strategy: The SunStrategy instance (for base class helpers)
    @param suit_probs: Optional Bayesian suit probabilities dict
    @returns Play decision dict
    """
    lead_suit = ctx.lead_suit
    winning_card = ctx.winning_card
    winner_pos = ctx.winner_pos

    follows = [i for i, c in enumerate(ctx.hand) if c.suit == lead_suit]
    if not follows:
        return strategy.get_trash_card(ctx)

    partner_pos = strategy.get_partner_pos(ctx.player_index)
    is_partner_winning = (winner_pos == partner_pos)

    # SEAT-AWARE POSITIONAL PLAY
    seat = len(ctx.table_cards) + 1  # 2nd, 3rd, or 4th seat

    # TRICK VALUE: Calculate how many points are on the table
    trick_points = 0
    for tc in ctx.table_cards:
        tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
        if isinstance(tc_card, dict):
            trick_points += POINT_VALUES_SUN.get(tc_card.get('rank', ''), 0)
        elif hasattr(tc_card, 'rank'):
            trick_points += POINT_VALUES_SUN.get(tc_card.rank, 0)

    # ── COOPERATIVE FOLLOW: Partner-aware follow override ──
    try:
        _pi = None
        if hasattr(ctx, 'read_partner_info'):
            try: _pi = ctx.read_partner_info()
            except Exception: pass
        if _pi:
            coop_f = get_cooperative_follow(
                hand=ctx.hand, legal_indices=follows, partner_info=_pi,
                led_suit=lead_suit, mode='SUN', trump_suit=None,
                partner_winning=is_partner_winning, trick_points=trick_points,
            )
            if coop_f and coop_f.get('confidence', 0) >= 0.6:
                logger.debug(f"[COOP_FOLLOW] {coop_f['tactic']}({coop_f['confidence']:.0%}): {coop_f['reasoning']}")
                return {"action": "PLAY", "cardIndex": coop_f['card_index'],
                        "reasoning": f"CoopFollow/{coop_f['tactic']}: {coop_f['reasoning']}"}
    except Exception as e:
        logger.debug(f"Cooperative follow skipped: {e}")

    # ── FOLLOW OPTIMIZER: Consult specialized follow-suit module ──
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
            led_suit=lead_suit, mode='SUN', trump_suit=None, seat=seat,
            partner_winning=is_partner_winning, partner_card_index=_partner_card_idx,
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

    if is_partner_winning:
        safe_feeds = []
        overtaking_feeds = []

        for idx in follows:
            c = ctx.hand[idx]
            if ctx._compare_ranks(c.rank, winning_card.rank, 'SUN'):
                overtaking_feeds.append(idx)
            else:
                safe_feeds.append(idx)

        if safe_feeds:
            best_idx = strategy.find_highest_point_card(ctx, safe_feeds, POINT_VALUES_SUN)
            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Partner winning - Safe Feed"}
        else:
            best_idx = strategy.find_lowest_rank_card(ctx, overtaking_feeds, ORDER_SUN)
            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Overtaking Partner (Forced)"}
    else:
        winners = []
        for idx in follows:
            c = ctx.hand[idx]
            if ctx._compare_ranks(c.rank, winning_card.rank, 'SUN'):
                winners.append(idx)

        if winners:
            if seat == 4:
                # 4TH SEAT: Guaranteed win — finesse with lowest winner
                best_idx = strategy.find_lowest_rank_card(ctx, winners, ORDER_SUN)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "4th Seat Finesse"}
            elif seat == 3:
                # 3RD SEAT: Partner already played, one opponent left.
                if trick_points >= 10:
                    best_idx = strategy.find_best_winner(ctx, winners, ORDER_SUN)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Securing High-Value Trick"}
                else:
                    best_idx = strategy.find_lowest_rank_card(ctx, winners, ORDER_SUN)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Economy Win"}
            else:
                # 2ND SEAT: Be conservative — partner hasn't played yet.
                master_winners = [i for i in winners if ctx.is_master_card(ctx.hand[i])]
                if master_winners:
                    best_idx = strategy.find_lowest_rank_card(ctx, master_winners, ORDER_SUN)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Playing Master"}
                elif trick_points >= 15:
                    best_idx = strategy.find_lowest_rank_card(ctx, winners, ORDER_SUN)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: High-Stakes Commit"}
                else:
                    best_idx = strategy.find_lowest_point_card(ctx, follows, POINT_VALUES_SUN)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Ducking for Partner"}
        else:
            # Can't win — POINT PROTECTION
            best_idx = strategy.find_lowest_point_card(ctx, follows, POINT_VALUES_SUN)
            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Ducking (Point Protection)"}
