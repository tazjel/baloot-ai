"""Sun defensive lead, Ashkal signal check, and partner signal reading.

Extracted from SunStrategy for file size reduction.
Pure functions that accept ctx (BotContext) and return decision dicts.
"""
from __future__ import annotations
import logging
from ai_worker.bot_context import BotContext

logger = logging.getLogger(__name__)


def get_defensive_lead_sun(ctx: BotContext, partner_pos: str) -> dict:
    """Defensive lead when OPPONENTS won the Sun bid.
    Strategy: Lead short suits to create voids, attack weak spots."""
    from ai_worker.strategies.components.defense_plan import plan_defense

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
        my_hand=ctx.hand, mode='SUN',
        buyer_position=buyer_pos, partner_position=partner_pos,
        tricks_played=len(tricks), tricks_won_by_us=our_wins, tricks_won_by_them=their_wins,
        void_suits=buyer_void_suits,
    )
    logger.debug(f"[DEFENSE] {dplan['reasoning']}")

    best_idx = 0
    max_score = -100

    # Calculate suit lengths
    suit_lengths: dict[str, int] = {}
    for s in ['♠', '♥', '♦', '♣']:
        suit_lengths[s] = sum(1 for c in ctx.hand if c.suit == s)

    for i, c in enumerate(ctx.hand):
        score = 0
        is_master = ctx.is_master_card(c)
        length = suit_lengths.get(c.suit, 0)

        # PRIORITY 1: Cash guaranteed masters — they can't lose
        if is_master:
            score += 80
            # Bonus for masters in short suits (extract value then get void)
            if length <= 2:
                score += 30

        # PRIORITY 2: Lead SHORT suits to create voids for future tricks
        if length == 1 and not is_master:
            score += 25  # Singleton — lead to void yourself
        elif length == 2:
            score += 15  # Doubleton

        # PRIORITY 3: Lead through declarer's WEAK suits
        # Attack suits where opponents showed weakness (discards)
        my_team = ctx.team
        for p in ctx.raw_state.get('players', []):
            if p.get('team') != my_team:
                # Bonus for leading suits where opponent is weak
                if ctx.memory:
                    remaining = ctx.memory.get_remaining_in_suit(c.suit)
                    if len(remaining) <= 2:  # Suit is nearly exhausted
                        score += 10

        # PENALTY: Don't lead unsupported honors (K without A, Q without K-A)
        if c.rank == 'K' and not any(x.rank == 'A' and x.suit == c.suit for x in ctx.hand):
            score -= 20  # Bare King = gift to opponents
        if c.rank == 'Q' and not any(x.rank in ['A', 'K'] and x.suit == c.suit for x in ctx.hand):
            score -= 15

        # PENALTY: Don't lead 10s and Aces into long contested suits (point hemorrhage)
        if c.rank in ['A', '10'] and not is_master and length >= 3:
            score -= 10

        if score > max_score:
            max_score = score
            best_idx = i

    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Defensive Lead (Sun)"}


def check_ashkal_signal(ctx: BotContext, partner_pos: str) -> dict | None:
    """Check if the game is in Ashkal state and if we need to respond to a color request."""
    bid = ctx.raw_state.get('bid', {})
    if not bid.get('isAshkal'):
        return None

    bidder_pos = bid.get('bidder')

    if bidder_pos != partner_pos:
        return None  # We only signal for partner's Ashkal

    round_num = bid.get('round', 1)

    floor_suit = None
    if ctx.floor_card:
        floor_suit = ctx.floor_card.suit
    elif ctx.raw_state.get('floorCard'):
        floor_suit = ctx.raw_state['floorCard'].get('suit')

    if not floor_suit:
        return None

    colors = {'♥': 'RED', '♦': 'RED', '♠': 'BLACK', '♣': 'BLACK'}
    floor_color = colors.get(floor_suit)

    target_color = None
    if round_num == 1:
        target_color = floor_color  # Same Color
    else:
        target_color = 'BLACK' if floor_color == 'RED' else 'RED'

    target_suits = [s for s, c in colors.items() if c == target_color]

    best_idx = -1
    max_score = -100

    for i, c in enumerate(ctx.hand):
        if c.suit in target_suits:
            score = 0
            if c.rank == 'A': score += 10
            elif c.rank == '10': score += 8
            elif c.rank == 'K': score += 6
            elif c.rank == 'Q': score += 4
            elif c.rank == 'J': score += 2
            else: score += 0

            if score > max_score:
                max_score = score
                best_idx = i

    if best_idx != -1:
        return {
            "action": "PLAY",
            "cardIndex": best_idx,
            "reasoning": f"Ashkal Response (Round {round_num}): Playing {target_color} for Partner"
        }

    return None


def check_partner_signals_sun(ctx: BotContext, partner_pos: str) -> dict | None:
    """Scans previous tricks to see if partner sent a signal (Sun mode)."""
    from ai_worker.signals.manager import SignalManager
    from ai_worker.signals.definitions import SignalType

    tricks = ctx.raw_state.get('currentRoundTricks', [])
    if not tricks: return None

    signal_mgr = SignalManager()

    last_trick = tricks[-1]
    cards = last_trick.get('cards', [])

    partner_card = None
    for c_data in cards:
        p_idx = c_data.get('playerIndex')
        my_idx = ctx.player_index
        partner_idx = (my_idx + 2) % 4

        if p_idx == partner_idx:
            from game_engine.models.card import Card
            partner_card = Card(c_data['suit'], c_data['rank'])
            break

    if not partner_card: return None

    if not cards: return None
    first_card_data = cards[0]
    actual_lead_suit = first_card_data['suit']

    if partner_card.suit != actual_lead_suit:
        winner_idx = last_trick.get('winner')
        is_tahreeb_context = (winner_idx == ctx.player_index)

        sig_type = signal_mgr.get_signal_for_card(partner_card, is_tahreeb_context)

        discards = ctx.memory.discards.get(partner_pos, [])
        directional_sig = signal_mgr.analyze_directional_signal(discards, partner_card.suit)

        if directional_sig == SignalType.CONFIRMED_POSITIVE:
            return {'suit': partner_card.suit, 'type': 'CONFIRMED_POSITIVE'}
        elif directional_sig == SignalType.CONFIRMED_NEGATIVE:
            return {'suit': partner_card.suit, 'type': 'CONFIRMED_NEGATIVE'}

        if sig_type == SignalType.URGENT_CALL:
            return {'suit': partner_card.suit, 'type': 'URGENT_CALL'}
        elif sig_type == SignalType.ENCOURAGE:
            return {'suit': partner_card.suit, 'type': 'ENCOURAGE'}
        elif sig_type == SignalType.NEGATIVE_DISCARD:
            discard_suit = partner_card.suit
            colors = {'♥': 'RED', '♦': 'RED', '♠': 'BLACK', '♣': 'BLACK'}
            my_color = colors.get(discard_suit)

            target_suits = []
            for s, color in colors.items():
                if color == my_color and s != discard_suit:
                    target_suits.append(s)

            return {'suits': target_suits, 'type': 'PREFER_SAME_COLOR', 'negated': discard_suit}
        elif sig_type == SignalType.PREFER_OPPOSITE_COLOR:
            discard_suit = partner_card.suit
            colors = {'♥': 'RED', '♦': 'RED', '♠': 'BLACK', '♣': 'BLACK'}
            my_color = colors.get(discard_suit)

            target_suits = []
            for s, color in colors.items():
                if color != my_color:
                    target_suits.append(s)

            return {'suits': target_suits, 'type': 'PREFER_OPPOSITE'}

    return None
