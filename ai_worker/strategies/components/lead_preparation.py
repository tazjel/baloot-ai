"""Shared lead_selector assembly and invocation for both SUN and HOKUM strategies.

Handles: collecting opponent voids, merging avoid suits from opp_model + trick_review
+ bid_reader, calling select_lead(), and adjusting confidence by trick_review.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def prepare_and_select_lead(
    ctx,
    mode: str,
    trump_suit: str | None,
    partner_pos: str,
    bidder_team: str,
    opp_model: dict | None,
    trick_review: dict | None,
    suit_probs: dict | None,
    trump_info: dict | None = None,
) -> dict | None:
    """Assemble context and call lead_selector with all available intelligence.

    Merges opponent voids, opp_model avoids, trick_review avoids, bid inference
    avoids, and adjusts confidence threshold based on trick_review strategy_shift.

    @param ctx: BotContext with hand, position, raw_state, team, memory, etc.
    @param mode: 'SUN' or 'HOKUM'.
    @param trump_suit: Trump suit for HOKUM, None for SUN.
    @param partner_pos: Partner position name.
    @param bidder_team: 'us' or 'them'.
    @param opp_model: Opponent model dict (from model_opponents), or None.
    @param trick_review: Trick review dict (from review_tricks), or None.
    @param suit_probs: Bayesian suit probabilities dict, or None.
    @param trump_info: Trump management plan dict (HOKUM only), or None.
    @returns Play decision dict if confidence meets threshold, else None.
    """
    from ai_worker.strategies.components.lead_selector import select_lead
    from ai_worker.strategies.components.bid_reader import infer_from_bids

    tricks = ctx.raw_state.get('currentRoundTricks', [])
    our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
    master_idx = [i for i, c in enumerate(ctx.hand) if ctx.is_master_card(c)]

    # Collect opponent voids
    _opp_voids: dict[str, set] = {}
    my_team = ctx.team
    for s in ['♠', '♥', '♦', '♣']:
        for p in ctx.raw_state.get('players', []):
            if p.get('team') != my_team and ctx.is_player_void(p.get('position'), s):
                _opp_voids.setdefault(s, set()).add(p.get('position'))

    # Partner read
    _pi = None
    if hasattr(ctx, 'read_partner_info'):
        try:
            _pi = ctx.read_partner_info()
        except Exception:
            pass

    # Merge opponent model's avoid suits into voids
    if opp_model:
        for avoid_s in opp_model.get('avoid_lead_suits', []):
            if avoid_s not in _opp_voids:
                _opp_voids[avoid_s] = {'opp_model'}

    # Merge trick_review avoid_suits into voids
    if trick_review:
        for avoid_s in trick_review.get('avoid_suits', []):
            if avoid_s not in _opp_voids:
                _opp_voids[avoid_s] = {'trick_review'}

    # Bid inference: use bid history for card reading
    try:
        bid_hist = ctx.raw_state.get('bidHistory', [])
        _fc = ctx.floor_card
        _fc_dict = {'suit': _fc.suit, 'rank': _fc.rank} if _fc else None
        bid_reads = infer_from_bids(
            my_position=ctx.position, bid_history=bid_hist,
            floor_card=_fc_dict, bidding_round=ctx.bidding_round,
        )
        for avoid_s in bid_reads.get('avoid_suits', []):
            if avoid_s not in _opp_voids:
                _opp_voids[avoid_s] = {'bid_reader'}
        logger.debug(f"[BID_READ] decl={bid_reads.get('declarer_position')} avoid={bid_reads.get('avoid_suits')} target={bid_reads.get('target_suits')}")
    except Exception as e:
        logger.debug(f"Bid reader skipped: {e}")

    # Build defense_info from opponent model
    _def_info = None
    if opp_model and not (bidder_team == 'us'):
        safe = opp_model.get('safe_lead_suits', [])
        _def_info = {
            'priority_suit': safe[0] if safe else None,
            'avoid_suit': opp_model.get('avoid_lead_suits', [None])[0] if opp_model.get('avoid_lead_suits') else None,
            'reasoning': opp_model.get('reasoning', ''),
        }

    ls_result = select_lead(
        hand=ctx.hand, mode=mode, trump_suit=trump_suit,
        we_are_buyers=(bidder_team == 'us'),
        tricks_played=len(tricks), tricks_won_by_us=our_wins,
        master_indices=master_idx, partner_info=_pi,
        defense_info=_def_info, trump_info=trump_info,
        opponent_voids=_opp_voids,
        suit_probs=suit_probs,
    )

    # Adjust confidence threshold based on trick_review strategy_shift
    _ls_threshold = 0.65
    if trick_review:
        shift = trick_review.get('strategy_shift', 'NONE')
        if shift == 'AGGRESSIVE':
            _ls_threshold = 0.50
        elif shift == 'DAMAGE_CONTROL':
            _ls_threshold = 0.75

    if ls_result and ls_result.get('confidence', 0) >= _ls_threshold:
        logger.debug(f"[LEAD_SEL] {ls_result['strategy']}({ls_result['confidence']:.0%}): {ls_result['reasoning']}")
        return {"action": "PLAY", "cardIndex": ls_result['card_index'],
                "reasoning": f"LeadSel/{ls_result['strategy']}: {ls_result['reasoning']}"}

    return None
