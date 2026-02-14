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
    Calibrated Sun hand evaluation.
    Analyzes: quick tricks, suit quality, stoppers, distribution, projects.
    Score roughly 0-50+. Threshold ~22 to bid.

    Calibration notes (v2):
    - Removed double-counting between quick tricks and HCP
    - Quick tricks are the PRIMARY valuation (trick-taking power)
    - HCP replaced with a lighter "honor density" bonus (avoids overlap)
    - Penalties for exposed suits are more aggressive
    - Stopper count gates: unstoppable suits = huge risk in SUN
    """
    score = 0

    # Group cards by suit
    suits = {}
    for c in hand:
        suits.setdefault(c.suit, []).append(c)

    # ── QUICK TRICKS (PRIMARY VALUATION) ──
    # Each suit is evaluated for guaranteed winning tricks
    quick_tricks = 0
    for s, cards in suits.items():
        ranks = [c.rank for c in cards]

        if 'A' in ranks:
            quick_tricks += 1  # Ace = 1 guaranteed trick
            if 'K' in ranks:
                quick_tricks += 0.5  # A-K = 1.5 tricks (K protected by A)
                if '10' in ranks:
                    quick_tricks += 0.5  # A-K-10 = 2 tricks (fully protected)
            elif '10' in ranks:
                quick_tricks += 0.3  # A-10 without K = partial protection
        elif 'K' in ranks:
            # Unprotected King — risky, only a fraction of a trick
            if len(cards) >= 3:
                quick_tricks += 0.5  # K with length = some chance
            elif len(cards) >= 2:
                quick_tricks += 0.3  # K with one cover

    score += quick_tricks * 5  # Each quick trick ≈ 5 points (reduced from 6)

    # ── HONOR DENSITY (replaces HCP to avoid double-counting) ──
    # Only count non-Ace honors that weren't already captured in quick tricks
    # This rewards depth of honors without re-counting Aces
    honor_density = 0
    for s, cards in suits.items():
        ranks = [c.rank for c in cards]
        length = len(cards)
        # Count supporting honors (not Aces — those are in quick tricks)
        for r in ranks:
            if r == '10' and 'A' not in ranks:
                honor_density += 2  # Unprotected 10 has value but risky
            elif r == '10' and 'A' in ranks:
                pass  # Already counted in quick tricks
            elif r == 'K' and 'A' not in ranks and length >= 2:
                honor_density += 1  # Protected K without Ace = some value
            elif r == 'Q' and length >= 2:
                honor_density += 0.5  # Queen with cover = minor value

    score += honor_density

    # ── SUIT QUALITY ──
    for s, cards in suits.items():
        ranks = [c.rank for c in cards]
        length = len(cards)

        # Long suit bonus — 4+ cards in a suit creates extra tricks
        if length >= 5:
            has_top = 'A' in ranks or ('K' in ranks and '10' in ranks)
            score += 4 if has_top else 2  # Long suit needs tops to run
        elif length >= 4:
            has_top = 'A' in ranks
            score += 2 if has_top else 1  # 4-card suit needs Ace to run

        # Isolated honors penalty — honor alone in a suit
        if length == 1:
            if ranks[0] in ['K', 'Q']:
                score -= 3  # Bare King/Queen = guaranteed loser
            elif ranks[0] in ['10']:
                score -= 3  # Bare 10 = almost guaranteed loser
            elif ranks[0] in ['7', '8', '9']:
                score -= 1  # Singleton low = opponent runs suit through

        # Unguarded suits penalty (no honor at all in a 2-card suit)
        if length == 2 and not any(r in ['A', 'K', 'Q'] for r in ranks):
            score -= 2  # Doubleton with no honors = suit runs against us

    # ── STOPPER COUNT (CRITICAL FOR SUN) ──
    # In SUN, opponents can run any unstoppable suit for free tricks
    stoppers = 0
    unstoppable_suits = []
    for s in ['♠', '♥', '♦', '♣']:
        cards = suits.get(s, [])
        ranks = [c.rank for c in cards]
        length = len(cards)
        if 'A' in ranks:
            stoppers += 1
        elif 'K' in ranks and length >= 2:
            stoppers += 1  # K with cover
        elif 'Q' in ranks and length >= 3:
            stoppers += 1  # Q with double cover
        elif length >= 4:
            stoppers += 1  # Pure length can stop (they run out)
        else:
            unstoppable_suits.append(s)

    if stoppers >= 4:
        score += 4  # All suits stopped — safe Sun hand
    elif stoppers >= 3:
        score += 2
    elif stoppers == 2:
        score -= 2  # Two unstoppable suits = dangerous
    elif stoppers <= 1:
        score -= 5  # Critical vulnerability — opponents run 2+ suits

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
