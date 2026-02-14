"""
Al-Ta'sheer Signaling Utilities — Shared by Sun and Hokum strategies.

Provides:
- Role detection (Buyer/Moushtari vs Defender)
- Kaboot logic (sweep attempt / sweep breaking)
- 10-management tactics (Lone 10 return, Sira sequence protection)
- Barqiya response timing
"""
from ai_worker.bot_context import BotContext
from game_engine.models.constants import ORDER_SUN, SUITS
import logging

logger = logging.getLogger(__name__)


def get_role(ctx: BotContext) -> str:
    """
    Determine if the bot is the BUYER (Moushtari) or DEFENDER.
    Buyer = the player (or their partner) who won the bid.
    """
    partner_pos = _partner_pos(ctx)
    bidder = ctx.bid_winner
    if bidder in (ctx.position, partner_pos):
        return 'BUYER'
    return 'DEFENDER'


def should_attempt_kaboot(ctx: BotContext) -> bool:
    """
    Check if the bot's team is in a position to attempt Kaboot (sweep all tricks).
    Conditions: Buyer team, won all tricks so far, and remaining hand is strong.
    """
    if get_role(ctx) != 'BUYER':
        return False

    # Check trick history — have we won every trick so far?
    tricks = ctx.raw_state.get('currentRoundTricks', [])
    if not tricks:
        return True  # No tricks played yet — possible

    partner_pos = _partner_pos(ctx)
    for trick in tricks:
        winner = trick.get('winner')
        if winner not in (ctx.position, partner_pos):
            return False  # Lost a trick — no Kaboot

    # Still possible — check hand strength
    master_count = sum(1 for c in ctx.hand if ctx.is_master_card(c))
    return master_count >= len(ctx.hand) // 2  # At least half masters


def should_break_kaboot(ctx: BotContext) -> bool:
    """
    As DEFENDER: Check if opponents are sweeping and we must prioritize winning
    even 1 trick to deny the Kaboot bonus.
    """
    if get_role(ctx) != 'DEFENDER':
        return False

    tricks = ctx.raw_state.get('currentRoundTricks', [])
    if len(tricks) < 2:
        return False  # Too early to tell

    partner_pos = _partner_pos(ctx)
    for trick in tricks:
        winner = trick.get('winner')
        if winner in (ctx.position, partner_pos):
            return False  # We already won a trick — no Kaboot threat

    return True  # All tricks lost so far — Kaboot danger!


def get_ten_management_play(ctx: BotContext, legal_indices: list) -> dict | None:
    """
    Professional 10-management tactics:
    
    1. LONE 10 RETURN: If holding only a 10 in a suit (no Ace/King protection),
       return it to partner early before opponents can capture it.
    
    2. SIRA SEQUENCE PROTECTION: If holding a sequence like 10-9-8, lead with
       the lowest card (8) to protect the high-value 10.
    
    3. MARDOUF AVOIDANCE: Don't lead an unprotected 10 late in the game.
    """
    if not legal_indices:
        return None

    mode = ctx.mode or 'SUN'
    point_order = ORDER_SUN  # 10 is high in Sun

    for idx in legal_indices:
        c = ctx.hand[idx]

        # 1. SIRA SEQUENCE: If we have consecutive cards, lead from bottom
        if c.rank == '10' and mode == 'SUN':
            suit_cards = [(i, ctx.hand[i]) for i in legal_indices if ctx.hand[i].suit == c.suit]
            suit_ranks = [sc[1].rank for sc in suit_cards]

            # Check for descending sequence from 10
            has_9 = '9' in suit_ranks
            has_8 = '8' in suit_ranks

            if has_9 and has_8 and len(suit_cards) >= 3:
                # Sira! Lead the lowest (8) to protect the 10
                lowest = min(suit_cards, key=lambda x: ORDER_SUN.index(x[1].rank) if x[1].rank in ORDER_SUN else -1)
                return {
                    "action": "PLAY",
                    "cardIndex": lowest[0],
                    "reasoning": f"Sira: Protecting 10 — leading {lowest[1].rank}{lowest[1].suit}"
                }

        # 2. LONE 10 RETURN: Unprotected 10 (no Ace in same suit)
        if c.rank == '10' and mode == 'SUN':
            suit_cards = [x for x in ctx.hand if x.suit == c.suit]
            suit_ranks = [x.rank for x in suit_cards]

            if 'A' not in suit_ranks and len(suit_cards) <= 2:
                tricks_played = len(ctx.raw_state.get('currentRoundTricks', []))
                if tricks_played <= 3:
                    # Lone 10 without Ace protection — lead it early to partner
                    # before opponents can set up to capture it
                    return {
                        "action": "PLAY",
                        "cardIndex": idx,
                        "reasoning": f"Lone 10 Return: Unprotected 10{c.suit} — returning early"
                    }

    return None


def get_barqiya_response(ctx: BotContext, signal: dict, legal_indices: list) -> dict | None:
    """
    Barqiya Response Timing:
    - LATE GAME (≤4 cards remaining): Respond IMMEDIATELY to partner's urgent signal
    - EARLY GAME (>4 cards remaining): Cash own masters first, then respond
    """
    if not signal or signal.get('type') != 'URGENT_CALL':
        return None

    target_suit = signal.get('suit')
    if not target_suit:
        return None

    cards_left = len(ctx.hand)
    responding_cards = [i for i in legal_indices if ctx.hand[i].suit == target_suit]

    if not responding_cards:
        return None

    if cards_left <= 4:
        # LATE GAME: Respond immediately — no time to waste
        # Lead highest card in the requested suit
        best_idx = responding_cards[0]
        best_strength = -1
        for i in responding_cards:
            try:
                strength = ORDER_SUN.index(ctx.hand[i].rank)
                if strength > best_strength:
                    best_strength = strength
                    best_idx = i
            except ValueError:
                continue
        return {
            "action": "PLAY",
            "cardIndex": best_idx,
            "reasoning": f"Barqiya URGENT: Late-game response to {target_suit}"
        }
    else:
        # EARLY GAME: Check if we have masters to cash first
        masters = [i for i in legal_indices if ctx.is_master_card(ctx.hand[i]) and ctx.hand[i].suit != target_suit]
        if masters:
            return None  # Cash masters first, respond later
        else:
            # No masters to cash — respond now
            best_idx = responding_cards[0]
            return {
                "action": "PLAY",
                "cardIndex": best_idx,
                "reasoning": f"Barqiya: Early-game response to {target_suit} (no masters to cash)"
            }


def _partner_pos(ctx: BotContext) -> str:
    """Get partner position name."""
    positions = ['Bottom', 'Right', 'Top', 'Left']
    partner_idx = (ctx.player_index + 2) % 4
    return positions[partner_idx]
