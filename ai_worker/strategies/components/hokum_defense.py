"""Hokum defensive lead and partner signal reading.

Extracted from HokumStrategy for file size reduction.
Pure functions that accept ctx (BotContext) and return decision dicts.
"""
from __future__ import annotations
import logging
from ai_worker.bot_context import BotContext

logger = logging.getLogger(__name__)


def get_defensive_lead_hokum(ctx: BotContext, partner_pos: str) -> dict:
    """Defensive lead when OPPONENTS won the Hokum bid.
    Strategy: Lead suits to create ruff opportunities, avoid feeding declarer."""
    from ai_worker.strategies.components.defense_plan import plan_defense
    trump = ctx.trump

    # Consult defensive planner for strategy guidance
    tricks = ctx.raw_state.get('currentRoundTricks', [])
    our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
    their_wins = len(tricks) - our_wins
    # Collect buyer's void suits from CardTracker for defense_plan
    buyer_void_suits = []
    buyer_pos = ctx.bid_winner or ''
    if buyer_pos:
        for s in ['♠', '♥', '♦', '♣']:
            if ctx.is_player_void(buyer_pos, s):
                buyer_void_suits.append(s)
    dplan = plan_defense(
        my_hand=ctx.hand, mode='HOKUM', trump_suit=trump,
        buyer_position=buyer_pos, partner_position=partner_pos,
        tricks_played=len(tricks), tricks_won_by_us=our_wins, tricks_won_by_them=their_wins,
        void_suits=buyer_void_suits,
    )
    logger.debug(f"[DEFENSE] {dplan['reasoning']}")

    best_idx = 0
    max_score = -100

    # Suit analysis
    suit_lengths: dict[str, int] = {}
    for s in ['♠', '♥', '♦', '♣']:
        suit_lengths[s] = sum(1 for c in ctx.hand if c.suit == s)

    # Check how many trumps WE have
    my_trump_count = suit_lengths.get(trump, 0)

    for i, c in enumerate(ctx.hand):
        score = 0
        is_trump = (c.suit == trump)
        is_master = ctx.is_master_card(c)
        length = suit_lengths.get(c.suit, 0)

        if is_trump:
            # DON'T lead trumps on defense — that helps declarer!
            # Exception: if we have J-9 (strongest trumps), lead to force their trumps out
            if c.rank in ['J', '9'] and my_trump_count >= 3:
                score += 20  # We can afford to draw trumps with dominant position
            else:
                score -= 40  # Don't waste trumps on defense
        else:
            # Non-trump leads
            if is_master:
                # Cash masters immediately — before declarer can ruff them
                score += 70
                if length <= 2:
                    score += 20  # Short-suit master = cash and get void fast

            # PRIORITY: Lead SHORT suits to create ruff opportunities
            if length == 1 and not is_master:
                score += 35  # Singleton — void yourself, ruff next time!
            elif length == 2 and not is_master:
                score += 20  # Doubleton

            # PENALTY: Don't lead bare honors into declarer's strength
            if c.rank == 'K' and not any(x.rank == 'A' and x.suit == c.suit for x in ctx.hand):
                score -= 25  # Bare King eaten by Ace
            if c.rank in ['10', 'A'] and not is_master:
                score -= 10  # Don't gift big points

            # BONUS: Lead suits where opponents are void (partner might ruff!)
            partner_might_ruff = False
            if ctx.is_player_void(partner_pos, c.suit):
                # Partner is void in this suit and might have trumps!
                if not ctx.is_player_void(partner_pos, trump):
                    partner_might_ruff = True
            if partner_might_ruff:
                score += 40  # Feed partner a ruff opportunity!

        if score > max_score:
            max_score = score
            best_idx = i

    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Defensive Lead (Hokum)"}


def check_partner_signals_hokum(ctx: BotContext, partner_pos: str) -> dict | None:
    """Scan previous tricks for partner discard signals (Hokum-specific).

    Hokum additions over Sun:
    - Trump discard by partner = "draw out their trumps" signal
    - Interpret Tahreeb vs Tanfeer context
    """
    tricks = ctx.raw_state.get('currentRoundTricks', [])
    if not tricks:
        return None

    trump = ctx.trump

    # Scan recent tricks (most recent first) for partner discards
    for trick in reversed(tricks):
        if not trick.get('cards'):
            continue

        # Find the led suit
        first_card = trick['cards'][0]
        fc = first_card if 'rank' in first_card else first_card.get('card', {})
        led_suit = fc.get('suit')

        # Determine trick winner for Tahreeb/Tanfeer context
        trick_winner = trick.get('winner')

        for i, c_data in enumerate(trick.get('cards', [])):
            c_inner = c_data if 'rank' in c_data else c_data.get('card', {})
            player_pos = c_data.get('playedBy')
            if not player_pos:
                played_by_list = trick.get('playedBy', [])
                if i < len(played_by_list):
                    player_pos = played_by_list[i]

            if player_pos != partner_pos:
                continue

            card_suit = c_inner.get('suit')
            card_rank = c_inner.get('rank')

            # Partner didn't follow suit — this is a signal!
            if card_suit and led_suit and card_suit != led_suit:
                # Was partner winning when they discarded? (Tahreeb vs Tanfeer)
                partner_won = (trick_winner == partner_pos)

                if not partner_won:
                    # TANFEER: Opponent won — partner signaling a want
                    if card_rank == 'A':
                        # BARQIYA! Sacrificing an Ace = urgent call
                        return {'type': 'URGENT_CALL', 'suit': card_suit, 'strength': 'HIGH'}
                    elif card_rank in ('K', 'Q', '10'):
                        return {'type': 'ENCOURAGE', 'suit': card_suit, 'strength': 'MEDIUM'}
                    else:
                        return {'type': 'ENCOURAGE', 'suit': card_suit, 'strength': 'LOW'}
                else:
                    # TAHREEB: Partner won — partner signaling to avoid
                    return {'type': 'NEGATIVE_DISCARD', 'suit': card_suit}

    return None
