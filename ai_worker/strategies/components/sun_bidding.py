"""
Sun Bidding Logic Component.

This module contains the logic for evaluating Sun hands, detecting Sun-specific
premium patterns, and making doubling decisions for Sun bids.
"""
from game_engine.models.constants import SUITS
from game_engine.logic.utils import scan_hand_for_projects
from ai_worker.bot_context import BotContext
import logging

logger = logging.getLogger(__name__)

def calculate_sun_strength(hand):
    """
    Advanced Sun hand evaluation.
    Analyzes: quick tricks, suit quality, stoppers, distribution, projects.
    Score roughly 0-50+. Threshold ~22 to bid.
    """
    score = 0

    # Group cards by suit
    suits = {}
    for c in hand:
        suits.setdefault(c.suit, []).append(c)

    # ── QUICK TRICKS ──
    # Each suit is evaluated for guaranteed winning tricks
    quick_tricks = 0
    for s, cards in suits.items():
        ranks = [c.rank for c in cards]

        if 'A' in ranks:
            quick_tricks += 1  # Ace = 1 guaranteed trick
            if 'K' in ranks:
                quick_tricks += 0.5  # A-K = 1.5 tricks (K protected by A)
            if '10' in ranks:
                quick_tricks += 0.5  # A-10 = Ace protects 10
        elif 'K' in ranks:
            # Unprotected King — risky, only half a trick
            if len(cards) >= 2:
                quick_tricks += 0.5  # K with length = some chance
            # K alone in a suit = loser (opponent leads Ace)

    score += quick_tricks * 6  # Each quick trick ≈ 6 points of score

    # ── HIGH CARD POINTS ──
    rank_values = {'A': 5, '10': 4, 'K': 3, 'Q': 2, 'J': 1}
    hcp = sum(rank_values.get(c.rank, 0) for c in hand)
    score += hcp

    # ── SUIT QUALITY ──
    for s, cards in suits.items():
        ranks = [c.rank for c in cards]
        length = len(cards)

        # Long suit bonus — 4+ cards in a suit creates extra tricks
        if length >= 5:
            score += 4  # Very long suit, lots of tricks
        elif length >= 4:
            score += 2  # Good length

        # Isolated honors penalty — Q or K alone in a suit
        if length == 1:
            if ranks[0] in ['K', 'Q']:
                score -= 3  # Bare King/Queen = loser
            elif ranks[0] in ['10']:
                score -= 2  # Bare 10 = likely loser
            elif ranks[0] in ['7', '8', '9']:
                score -= 1  # Singleton low = gets trumped (but this is Sun)

        # Honor combinations
        if 'A' in ranks and 'K' in ranks and '10' in ranks:
            score += 3  # A-K-10 = commanding suit
        elif 'A' in ranks and 'K' in ranks:
            score += 2  # A-K = solid control
        elif 'K' in ranks and 'Q' in ranks:
            score += 1  # K-Q = some control

        # Unguarded suits penalty (no honor at all in a 2-card suit)
        if length == 2 and not any(r in ['A', 'K', 'Q'] for r in ranks):
            score -= 1  # Doubleton with no honors

    # ── STOPPER COUNT ──
    # Suits where we can stop opponent's leads
    stoppers = 0
    for s, cards in suits.items():
        ranks = [c.rank for c in cards]
        if 'A' in ranks:
            stoppers += 1
        elif 'K' in ranks and len(cards) >= 2:
            stoppers += 1  # K with cover
        elif 'Q' in ranks and len(cards) >= 3:
            stoppers += 1  # Q with double cover

    if stoppers >= 4:
        score += 4  # All suits stopped — safe Sun hand
    elif stoppers >= 3:
        score += 2
    elif stoppers <= 1:
        score -= 3  # Too many exposed suits

    # ── PROJECTS ──
    projects = scan_hand_for_projects(hand, 'SUN')
    if projects:
         for p in projects:
              raw_val = p.get('score', 0)
              if raw_val >= 100:
                  score += 6  # Strong project bonus
              elif raw_val >= 50:
                  score += 3

    # ── 4-OF-A-KIND BONUSES ──
    ranks_list = [c.rank for c in hand]
    if ranks_list.count('A') >= 3: score += 4
    if ranks_list.count('A') == 4: score += 8  # 4 Aces = dominant
    if ranks_list.count('10') >= 3: score += 2

    return max(0, score)

def detect_sun_premium_pattern(ctx: BotContext):
    """
    Checks for Sun-specific premium patterns:
    - 400: 4 Aces in Sun (40-point project)
    - Miya: 5-card sequence (A-K-Q-J-10) in Sun (100 project)
    - Ruler of the Board: 3+ Aces + 2+ Tens
    """
    if not ctx.floor_card:
        return None

    fc = ctx.floor_card
    hand_ranks = [c.rank for c in ctx.hand]
    combined_ranks = hand_ranks + [fc.rank]

    # === 400 (Sun): 4 Aces ===
    if combined_ranks.count('A') >= 4:
        return {"action": "SUN",
                "reasoning": "400 Project: 4 Aces (40-point bonus)"}

    # === MIYA (Sun): 5-card sequence A-K-Q-J-10 in same suit ===
    for suit in SUITS:
        suit_ranks = [c.rank for c in ctx.hand if c.suit == suit]
        if fc.suit == suit:
            suit_ranks.append(fc.rank)
        miya_set = {'A', 'K', 'Q', 'J', '10'}
        if miya_set.issubset(set(suit_ranks)):
            return {"action": "SUN",
                    "reasoning": f"MIYA: 5-card sequence in {suit} (100 project)"}

    # === RULER OF THE BOARD (Sun): 3+ Aces + 2+ Tens ===
    ace_count = combined_ranks.count('A')
    ten_count = combined_ranks.count('10')
    if ace_count >= 3 and ten_count >= 2:
        return {"action": "SUN",
                "reasoning": f"Ruler: {ace_count} Aces + {ten_count} Tens"}

    return None

def evaluate_sun_doubling(ctx: BotContext):
    """Evaluate if we should double a Sun bid."""
    # Count Aces (key to blocking Sun)
    aces = sum(1 for c in ctx.hand if c.rank == 'A')
    tens = sum(1 for c in ctx.hand if c.rank == '10')

    # 3+ Aces = they can't win most tricks
    if aces >= 3:
        return {"action": "DOUBLE", "reasoning": f"Punishing Sun: {aces} Aces"}

    # 2 Aces + strong supporting honors
    if aces >= 2 and tens >= 2:
        return {"action": "DOUBLE", "reasoning": f"Punishing Sun: {aces}A + {tens}×10"}

    return None
