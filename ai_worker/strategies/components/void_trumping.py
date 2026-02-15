"""Seat-aware void trumping decisions for Hokum mode.

Pure-function module extracted from HokumStrategy._get_hokum_follow() for testability.
"""
from __future__ import annotations
import logging
from game_engine.models.constants import ORDER_HOKUM

logger = logging.getLogger(__name__)


def decide_void_trump(ctx, trump_suit: str, winning_card, seat: int,
                      trick_points: int, is_partner_winning: bool) -> dict | None:
    """Decide trumping action when void in led suit (Hokum mode).

    Implements seat-aware trump economy:
    - 4th seat: guaranteed win with lowest trump
    - 2nd seat: conservative, only trump high-value tricks
    - 3rd seat: aggressive trumping
    - Over-trump logic when current winner has trumped

    @param ctx: BotContext with hand, _compare_ranks, find_lowest_rank_card via base.
    @param trump_suit: The trump suit string.
    @param winning_card: The currently winning Card object.
    @param seat: Seat position (2, 3, or 4).
    @param trick_points: Total points in the current trick.
    @param is_partner_winning: Whether partner is currently winning the trick.
    @returns Play decision dict, or None if caller should use get_trash_card.
    """
    has_trumps = any(c.suit == trump_suit for c in ctx.hand)

    if has_trumps and not is_partner_winning:
        trumps = [i for i, c in enumerate(ctx.hand) if c.suit == trump_suit]

        if winning_card.suit == trump_suit:
            # Over-trump logic
            over_trumps = [i for i in trumps
                           if ctx._compare_ranks(ctx.hand[i].rank, winning_card.rank, 'HOKUM')]
            if over_trumps:
                best_idx = _find_lowest_rank(ctx, over_trumps)
                return {"action": "PLAY", "cardIndex": best_idx,
                        "reasoning": f"Seat {seat}: Over-trumping (Economy)"}
            else:
                return None  # Caller should get_trash_card
        else:
            # SMART TRUMPING: Consider trick value and seat position
            low_trumps = [i for i in trumps if ctx.hand[i].rank in ['7', '8', 'Q', 'K']]
            high_trumps = [i for i in trumps if ctx.hand[i].rank in ['J', '9', 'A', '10']]

            if seat == 4:
                # 4TH SEAT: Guaranteed win — use lowest trump always
                best_idx = _find_lowest_rank(ctx, trumps)
                return {"action": "PLAY", "cardIndex": best_idx,
                        "reasoning": "4th Seat: Guaranteed Trump"}
            elif seat == 2:
                # 2ND SEAT: Conservative — only trump high-value tricks
                if trick_points >= 10 or not high_trumps:
                    if low_trumps:
                        best_idx = _find_lowest_rank(ctx, low_trumps)
                        return {"action": "PLAY", "cardIndex": best_idx,
                                "reasoning": "2nd Seat: Cheap Trump (Worth It)"}
                    else:
                        best_idx = _find_lowest_rank(ctx, trumps)
                        return {"action": "PLAY", "cardIndex": best_idx,
                                "reasoning": "2nd Seat: Forced Trump"}
                else:
                    # Low value, partner might handle it — discard instead
                    return None  # Caller should get_trash_card
            else:
                # 3RD SEAT: Aggressive trumping
                if trick_points >= 10 or not high_trumps:
                    best_idx = _find_lowest_rank(ctx, trumps)
                    return {"action": "PLAY", "cardIndex": best_idx,
                            "reasoning": "3rd Seat: Eating with Trump"}
                elif low_trumps:
                    best_idx = _find_lowest_rank(ctx, low_trumps)
                    return {"action": "PLAY", "cardIndex": best_idx,
                            "reasoning": "3rd Seat: Cheap Trump Eat"}
                else:
                    return None  # Caller should get_trash_card

    # has_trumps and partner_winning, or no trumps → caller should get_trash_card
    return None


def _find_lowest_rank(ctx, indices: list) -> int:
    """Find the lowest-ranked card among indices using HOKUM ordering."""
    best_i = indices[0]
    min_strength = 999
    for i in indices:
        try:
            strength = ORDER_HOKUM.index(ctx.hand[i].rank)
        except ValueError:
            strength = 0
        if strength < min_strength:
            min_strength = strength
            best_i = i
    return best_i
