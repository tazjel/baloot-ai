"""Personality filter — modify play decisions based on bot personality.

Pure function: apply_personality_to_play(decision, ctx) -> modified decision.
Called AFTER the strategy returns a decision but BEFORE legality enforcement.

Does NOT change which cards are legal — only reorders preference among legal options.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from ai_worker.strategies.constants import PTS_SUN, PTS_HOKUM

logger = logging.getLogger(__name__)


def apply_personality_to_play(
    decision: dict,
    ctx,
    legal_indices: list[int],
) -> dict:
    """Apply personality-based play modifications.

    Personality attributes used:
    - trump_lead_bias: Preference for leading trumps (HOKUM)
    - point_greed: Chase high-point tricks vs protect points
    - risk_tolerance: Willingness to play risky cards
    - kaboot_pursuit: Override to pursue Kaboot sweep
    - false_signal_rate: Chance of deceptive play (misleading discard)
    - partner_trust: Affects following partner signals

    Args:
        decision: Current play decision dict with 'action', 'cardIndex', 'reasoning'.
        ctx: BotContext with hand, mode, personality, table_cards, etc.
        legal_indices: List of legal card indices.

    Returns:
        Modified decision dict (or original if no personality change needed).
    """
    if not decision or decision.get('action') != 'PLAY':
        return decision

    if not legal_indices or len(legal_indices) <= 1:
        return decision  # No choice to make

    personality = getattr(ctx, 'personality', None)
    if personality is None:
        return decision

    hand = ctx.hand
    if not hand:
        return decision

    chosen_idx = decision.get('cardIndex')

    try:
        # --- FALSE SIGNAL: Deceptive play ---
        if personality.false_signal_rate > 0 and random.random() < personality.false_signal_rate:
            deceptive = _try_deceptive_play(ctx, legal_indices, chosen_idx)
            if deceptive is not None and deceptive != chosen_idx:
                logger.debug(f"[PERSONALITY] {personality.name}: Deceptive play idx={chosen_idx} -> {deceptive}")
                return {
                    **decision,
                    'cardIndex': deceptive,
                    'reasoning': decision.get('reasoning', '') + f" (Tricky: deceptive play)"
                }

        # --- TRUMP LEAD BIAS (HOKUM only, when leading) ---
        if ctx.mode == 'HOKUM' and not ctx.table_cards and personality.trump_lead_bias != 0.5:
            override = _apply_trump_lead_bias(ctx, legal_indices, chosen_idx, personality.trump_lead_bias)
            if override is not None and override != chosen_idx:
                logger.debug(f"[PERSONALITY] {personality.name}: Trump lead bias idx={chosen_idx} -> {override}")
                return {
                    **decision,
                    'cardIndex': override,
                    'reasoning': decision.get('reasoning', '') + f" (Personality: trump_lead_bias={personality.trump_lead_bias:.1f})"
                }

        # --- POINT GREED: Chase or protect high-value tricks ---
        if personality.point_greed != 0.5 and ctx.table_cards:
            override = _apply_point_greed(ctx, legal_indices, chosen_idx, personality.point_greed)
            if override is not None and override != chosen_idx:
                logger.debug(f"[PERSONALITY] {personality.name}: Point greed idx={chosen_idx} -> {override}")
                return {
                    **decision,
                    'cardIndex': override,
                    'reasoning': decision.get('reasoning', '') + f" (Personality: point_greed={personality.point_greed:.1f})"
                }

    except Exception as e:
        logger.warning(f"[PERSONALITY] Error in apply_personality_to_play: {e}")

    return decision


def _try_deceptive_play(ctx, legal_indices: list[int], current_idx: int) -> Optional[int]:
    """Attempt a deceptive play — underplay early, surprise late.

    Deceptive strategies:
    - Leading: play a low card from a strong suit (hide strength)
    - Following: play a non-obvious card (not the cheapest or most expensive)
    """
    hand = ctx.hand
    if len(legal_indices) < 3:
        return None  # Need 3+ options for deception

    # If leading (no table cards), underplay — choose a middling card
    if not ctx.table_cards:
        pts = PTS_SUN if ctx.mode == 'SUN' else PTS_HOKUM
        scored = [(i, pts.get(hand[i].rank, 0)) for i in legal_indices]
        scored.sort(key=lambda x: x[1])
        # Pick a middle card (not lowest, not highest)
        mid = len(scored) // 2
        return scored[mid][0]

    # If following, pick a random legal card that's not the current choice
    alternatives = [i for i in legal_indices if i != current_idx]
    return random.choice(alternatives) if alternatives else None


def _apply_trump_lead_bias(
    ctx, legal_indices: list[int], current_idx: int, bias: float
) -> Optional[int]:
    """Apply trump lead preference when leading in HOKUM.

    bias > 0.5: Prefer leading trumps
    bias < 0.5: Prefer avoiding trump leads (save for later)
    """
    hand = ctx.hand
    trump = ctx.trump

    trump_indices = [i for i in legal_indices if hand[i].suit == trump]
    non_trump_indices = [i for i in legal_indices if hand[i].suit != trump]

    if not trump_indices or not non_trump_indices:
        return None  # Can't switch either way

    current_is_trump = current_idx in trump_indices

    # High bias (>0.5) and currently NOT leading trump → switch to trump
    if bias > 0.6 and not current_is_trump:
        # Pick highest trump for aggressive lead
        from ai_worker.strategies.constants import ORDER_HOKUM
        best_trump = max(trump_indices, key=lambda i: ORDER_HOKUM.index(hand[i].rank) if hand[i].rank in ORDER_HOKUM else 0)
        return best_trump

    # Low bias (<0.4) and currently leading trump → switch to non-trump
    if bias < 0.4 and current_is_trump:
        # Pick safest non-trump (lowest value)
        pts = PTS_HOKUM
        safest = min(non_trump_indices, key=lambda i: pts.get(hand[i].rank, 0))
        return safest

    return None


def _apply_point_greed(
    ctx, legal_indices: list[int], current_idx: int, greed: float
) -> Optional[int]:
    """Apply point greed — chase or protect high-value tricks.

    greed > 0.5: Prefer playing high-value cards to win big tricks
    greed < 0.5: Prefer protecting points (play low, save high cards)
    """
    hand = ctx.hand
    pts = PTS_SUN if ctx.mode == 'SUN' else PTS_HOKUM

    # Calculate current trick value
    trick_value = sum(pts.get(tc.get('card', {}).get('rank', '7') if isinstance(tc, dict) else getattr(tc.get('card', None), 'rank', '7'), 0) for tc in ctx.table_cards)

    # High greed + valuable trick → play highest beater
    if greed > 0.7 and trick_value >= 15:
        scored = [(i, pts.get(hand[i].rank, 0)) for i in legal_indices]
        scored.sort(key=lambda x: x[1], reverse=True)
        if scored[0][0] != current_idx:
            return scored[0][0]

    # Low greed + low-value trick → play cheapest card
    if greed < 0.3 and trick_value < 10:
        scored = [(i, pts.get(hand[i].rank, 0)) for i in legal_indices]
        scored.sort(key=lambda x: x[1])
        if scored[0][0] != current_idx:
            return scored[0][0]

    return None
