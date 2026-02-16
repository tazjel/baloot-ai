"""Heuristic fallback lead scoring for when lead_selector confidence is insufficient.

Pure-function module extracted from HokumStrategy and SunStrategy for testability.

Empirical calibration from 109 professional games (32,449 plays):
- Lead rank preferences vary by trick number (early vs late game)
- Trick 1: A (40.2%), J (18.0%), K (9.1%) — pros lead Aces first
- Trick 7+: K (17.2%), 10 (16.5%), A (16.0%) — late game = run winners
- Bidder prefers: A > 10 > J > K > 9 > Q > 8 > 7
- Defender prefers: A > K > 10 > J > Q > 9 > 8 > 7
"""
from __future__ import annotations
import logging
from game_engine.models.constants import ORDER_SUN
from ai_worker.strategies.components.pro_data import (
    get_lead_weight, HOKUM_TRUMP_LEAD_PCT,
    BIDDER_LEAD_RANK_ORDER, DEFENDER_LEAD_RANK_ORDER,
)

logger = logging.getLogger(__name__)


def score_hokum_lead(ctx, trump: str, should_open_trump: bool,
                     remaining_enemy_trumps: int, ruffable_suits: set) -> dict:
    """Heuristic fallback scoring for Hokum lead card selection.

    Iterates hand, scores each card based on master status, rank, void danger,
    suit length, trump timing, card counting, and empirical pro lead preferences.

    @param ctx: BotContext with hand, is_master_card, is_player_void, memory, etc.
    @param trump: The trump suit string.
    @param should_open_trump: Whether trump manager recommends leading trump.
    @param remaining_enemy_trumps: Estimated number of enemy trumps remaining.
    @param ruffable_suits: Set of suits where opponents are void (ruff danger).
    @returns Play decision dict with 'action', 'cardIndex', 'reasoning'.
    """
    best_card_idx = 0
    max_score = -100
    my_team = ctx.team

    # Determine trick number for empirical lead rank preferences
    tricks_played = len(ctx.raw_state.get('currentRoundTricks', []))
    trick_number = tricks_played + 1  # 1-indexed

    for i, c in enumerate(ctx.hand):
        score = 0
        is_trump = (c.suit == trump)
        is_master = ctx.is_master_card(c)

        # ── EMPIRICAL LEAD RANK PREFERENCE (from 109 pro games) ──
        # Weight each card by how often pros lead this rank at this trick
        pro_weight = get_lead_weight(trick_number, c.rank)
        score += int(pro_weight * 30)  # Scale: 0.40 → +12, 0.05 → +1

        # VOID AVOIDANCE: Check if opponents are void in this suit
        is_danger = False
        if not is_trump:
            for p in ctx.raw_state.get('players', []):
                if p.get('team') != my_team:
                    if ctx.is_player_void(p.get('position'), c.suit):
                        is_danger = True
                        break

        if is_trump:
            if should_open_trump:
                score += 40

            master_bonus = 100
            if not (remaining_enemy_trumps > 0):
                master_bonus = 10  # Save for ruffing

            if is_master:
                score += master_bonus
            elif c.rank == 'J':
                if should_open_trump:
                    score += 80
                else:
                    score += 10
            elif c.rank == '9':
                if should_open_trump:
                    score += 60
                else:
                    score += 5
            else:
                score += 10
        else:
            # Non-Trump
            if is_master:
                score += 50
            elif c.rank == 'A':
                score += 30
            else:
                has_ace = any(x.rank == 'A' and x.suit == c.suit for x in ctx.hand)
                if not has_ace:
                    if c.rank == 'K': score -= 15
                    elif c.rank == 'Q': score -= 10
                    elif c.rank == 'J': score -= 5

            if is_danger:
                score -= 200  # NUCLEAR DETERRENT

            # CROSS-RUFF PENALTY: If this suit is ruffable, heavy penalty
            if c.suit in ruffable_suits:
                score -= 50

            # CARD COUNTING: Use memory to check remaining cards
            if ctx.memory:
                remaining = ctx.memory.get_remaining_in_suit(c.suit)
                remaining_ranks = [r['rank'] for r in remaining if r['rank'] != c.rank]

                # Penalize leading non-masters into contested suits
                if not is_master and remaining_ranks:
                    higher_exists = False
                    for r in remaining_ranks:
                        try:
                            if ORDER_SUN.index(r) > ORDER_SUN.index(c.rank):
                                higher_exists = True
                                break
                        except ValueError:
                            continue
                    if higher_exists:
                        score -= 10

                # SINGLETON DANGER: A lone non-master card gets eaten
                suit_count = sum(1 for x in ctx.hand if x.suit == c.suit)
                if suit_count == 1 and not is_master:
                    score -= 20  # Lone card that can't win

            # SUIT LENGTH: Prefer leading from long suits
            suit_count = sum(1 for x in ctx.hand if x.suit == c.suit)
            score += suit_count * 3

        if score > max_score:
            max_score = score
            best_card_idx = i

    reason = "Hokum Lead"
    if ctx.is_master_card(ctx.hand[best_card_idx]):
        reason = "Leading Master Card"
    if ctx.hand[best_card_idx].suit == trump and should_open_trump:
        reason = "Smart Sahn (Drawing Trumps)"

    return {"action": "PLAY", "cardIndex": best_card_idx, "reasoning": reason}


def score_sun_lead(ctx) -> dict:
    """Heuristic fallback scoring for Sun lead card selection.

    Iterates hand, scores each card based on master status, rank, void danger,
    suit length, card counting, and empirical pro lead preferences.

    @param ctx: BotContext with hand, is_master_card, is_player_void, memory, team, etc.
    @returns Play decision dict with 'action', 'cardIndex', 'reasoning'.
    """
    best_card_idx = 0
    max_score = -100

    # Determine trick number for empirical lead rank preferences
    tricks_played = len(ctx.raw_state.get('currentRoundTricks', []))
    trick_number = tricks_played + 1  # 1-indexed

    for i, c in enumerate(ctx.hand):
        score = 0
        is_master = ctx.is_master_card(c)

        # ── EMPIRICAL LEAD RANK PREFERENCE (from 109 pro games) ──
        pro_weight = get_lead_weight(trick_number, c.rank)
        score += int(pro_weight * 30)  # Scale: 0.40 → +12, 0.05 → +1

        if is_master:
            score += 100

        rank = c.rank
        if rank == 'A': score += 20
        elif rank == '10': score += 15
        elif rank == 'K':
            if any(x.rank == 'A' and x.suit == c.suit for x in ctx.hand): score += 18
            else: score += 5

        if rank in ['7', '8']: score += 2
        if rank in ['Q', 'J'] and not any(x.rank in ['A', 'K'] and x.suit == c.suit for x in ctx.hand):
            score -= 10

        # CARD COUNTING: Check remaining cards in this suit
        if ctx.memory:
            remaining_in_suit = ctx.memory.get_remaining_in_suit(c.suit)
            remaining_ranks = [r['rank'] for r in remaining_in_suit if r['rank'] != c.rank]

            # Penalize leading non-master cards into suits with higher remaining cards
            if not is_master and remaining_ranks:
                higher_exists = False
                for r in remaining_ranks:
                    try:
                        if ORDER_SUN.index(r) > ORDER_SUN.index(c.rank):
                            higher_exists = True
                            break
                    except ValueError:
                        continue
                if higher_exists:
                    score -= 15

            # BONUS: If suit has only 1-2 remaining cards and we have the master
            if is_master and len(remaining_in_suit) <= 3:
                score += 10

        # VOID DANGER: Avoid leading suits where opponents are void
        my_team = ctx.team
        for p in ctx.raw_state.get('players', []):
            if p.get('team') != my_team:
                if ctx.is_player_void(p.get('position'), c.suit):
                    score -= 30
                    break

        # SUIT LENGTH: Prefer leading from long suits (more control)
        suit_count = sum(1 for x in ctx.hand if x.suit == c.suit)
        score += suit_count * 3

        if score > max_score:
            max_score = score
            best_card_idx = i

    reason = "Sun Lead"
    if ctx.is_master_card(ctx.hand[best_card_idx]):
        reason = "Leading Master Card"

    return {"action": "PLAY", "cardIndex": best_card_idx, "reasoning": reason}
