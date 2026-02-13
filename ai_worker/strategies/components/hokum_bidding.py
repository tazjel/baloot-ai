"""
Hokum Bidding Logic Component.

This module contains the logic for evaluating Hokum hands, detecting Hokum-specific
premium patterns, and making doubling decisions for Hokum bids.
"""
from game_engine.models.constants import SUITS
from game_engine.logic.utils import scan_hand_for_projects
from ai_worker.bot_context import BotContext
import logging

logger = logging.getLogger(__name__)

def calculate_hokum_strength(hand, trump_suit):
    """
    Advanced Hokum hand evaluation.
    Analyzes: trump power, trump length, distribution, side aces, losers.
    Score roughly 0-50+. Threshold ~18 to bid.
    """
    score = 0

    # Group cards by suit
    suits = {}
    for c in hand:
        suits.setdefault(c.suit, []).append(c)

    my_trumps = suits.get(trump_suit, [])
    trump_ranks = [c.rank for c in my_trumps]
    trump_count = len(my_trumps)

    # ── TRUMP POWER ──
    # J (20pts, rank 1) and 9 (14pts, rank 2) are the kings of Hokum
    has_j = 'J' in trump_ranks
    has_9 = '9' in trump_ranks
    has_a = 'A' in trump_ranks
    has_10 = '10' in trump_ranks
    has_k = 'K' in trump_ranks

    # Individual trump values
    if has_j:  score += 12  # Jack of trump = dominant
    if has_9:  score += 10  # 9 of trump = second strongest
    if has_a:  score += 5   # Ace of trump
    if has_10: score += 4   # 10 of trump (high points)
    if has_k:  score += 2   # King of trump

    # ── TRUMP COMBOS ──
    if has_j and has_9:
        score += 6  # J-9 combo = near-unstoppable trump control
    if has_j and has_9 and has_a:
        score += 4  # J-9-A = completely dominant (extra bonus)
    if has_j and has_a and not has_9:
        score += 2  # J-A = strong but missing 9

    # ── TRUMP LENGTH ──
    if trump_count >= 5:
        score += 6  # 5+ trumps = can always ruff
    elif trump_count >= 4:
        score += 4  # 4 trumps = solid base
    elif trump_count >= 3:
        score += 2  # 3 trumps = minimum
    elif trump_count == 2:
        score -= 2  # Only 2 trumps = risky
    elif trump_count <= 1:
        score -= 8  # 0-1 trumps = terrible for Hokum

    # ── SIDE ACES ──
    # Non-trump Aces = guaranteed tricks that don't cost trumps
    side_aces = sum(1 for c in hand if c.rank == 'A' and c.suit != trump_suit)
    score += side_aces * 5  # Each side Ace = 5 points (very valuable)

    # Side Kings with Aces = extra strength
    for s, cards in suits.items():
        if s == trump_suit: continue
        ranks = [c.rank for c in cards]
        if 'A' in ranks and 'K' in ranks:
            score += 2  # A-K in same side suit = 2 tricks
        elif 'A' in ranks and '10' in ranks:
            score += 1  # A-10 in same side suit

    # ── DISTRIBUTION (Voids & Singletons) ──
    # Short side suits = can ruff with trumps
    for s in SUITS:
        if s == trump_suit: continue
        count = len(suits.get(s, []))
        if count == 0:
            score += 4  # Void = can ruff immediately
        elif count == 1:
            score += 2  # Singleton = ruff after 1 round
            # Singleton Ace is best — win the trick then ruff next
            singleton = suits[s][0] if suits.get(s) else None
            if singleton and singleton.rank == 'A':
                score += 2  # Singleton Ace = win trick then void!

    # ── LOSER COUNT (inverted) ──
    # Count expected losing cards
    losers = 0
    for s, cards in suits.items():
        if s == trump_suit:
            # Trump losers = cards below J-9-A that aren't in the top
            for c in cards:
                if c.rank in ['7', '8']:
                    losers += 0.5  # Low trumps sometimes lose
        else:
            ranks = [c.rank for c in cards]
            length = len(cards)
            if length == 0:
                continue  # Void = good
            elif length == 1:
                if ranks[0] not in ['A']:
                    losers += 1  # Singleton non-ace = loser
            elif length >= 2:
                # Each card beyond the first that isn't A/K is a potential loser
                covered = 0
                if 'A' in ranks: covered += 1
                if 'K' in ranks and length >= 2: covered += 1
                losers += max(0, min(3, length - covered))  # Cap at 3 losers per suit

    # Low losers = strong hand
    if losers <= 2:
        score += 4
    elif losers <= 3:
        score += 2
    elif losers >= 6:
        score -= 4

    # ── PROJECTS ──
    projects = scan_hand_for_projects(hand, 'HOKUM')
    if projects:
         for p in projects:
              raw_val = p.get('score', 0)
              score += (raw_val / 10)  # 100-point project ≈ +10

    return max(0, score)

def detect_hokum_premium_pattern(ctx: BotContext):
    """
    Checks for Hokum-specific premium patterns:
    - Lockdown: Top 4 trumps in Hokum (J, 9, A, 10)
    - Baloot: K+Q of trump + J for Hokum project bonus

    Only applies in Round 1 when floor card matches the suit.
    """
    if not ctx.floor_card or ctx.bidding_round != 1:
        return None

    fc = ctx.floor_card
    floor_suit = fc.suit
    hand_trump_ranks = [c.rank for c in ctx.hand if c.suit == floor_suit]
    combined_trump = hand_trump_ranks + [fc.rank]

    # === LOCKDOWN (Hokum): Top 4 trumps ===
    # In Hokum order: J > 9 > A > 10
    lockdown_cards = {'J', '9', 'A', '10'}
    if lockdown_cards.issubset(set(combined_trump)):
        return {"action": "HOKUM", "suit": floor_suit,
                "reasoning": f"LOCKDOWN: Top 4 trumps in {floor_suit} (J-9-A-10)"}

    # === BALOOT SETUP (Hokum): K+Q of trump + J ===
    if 'J' in hand_trump_ranks:  # Must have Jack for strength
        if 'K' in combined_trump and 'Q' in combined_trump:
            return {"action": "HOKUM", "suit": floor_suit,
                    "reasoning": f"BALOOT Setup: J + K+Q of {floor_suit}"}

    return None

def evaluate_hokum_doubling(ctx: BotContext):
    """Evaluate if we should double a Hokum bid."""
    bid = ctx.raw_state.get('bid', {})
    trump = bid.get('suit')
    if trump:
        # Count our trumps
        my_trumps = [c for c in ctx.hand if c.suit == trump]
        trump_ranks = [c.rank for c in my_trumps]

        # Holding J or 9 of trump = we control the trump suit
        has_j = 'J' in trump_ranks
        has_9 = '9' in trump_ranks

        if has_j and has_9:
            return {"action": "DOUBLE", "reasoning": f"Punishing Hokum: We hold J+9 of {trump}"}

        if has_j and len(my_trumps) >= 3:
            return {"action": "DOUBLE", "reasoning": f"Trump wall: J + {len(my_trumps)} trumps"}

    return None
