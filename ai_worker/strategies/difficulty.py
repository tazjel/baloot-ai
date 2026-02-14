"""Difficulty system — apply_difficulty() pure function.

Modifies bot decisions based on difficulty level to create
varied challenge. Lower levels introduce controlled mistakes;
higher levels unlock advanced features.

Usage:
    from ai_worker.strategies.difficulty import apply_difficulty, DifficultyLevel
    decision = apply_difficulty(decision, DifficultyLevel.EASY, ctx)
"""
from __future__ import annotations

import logging
import random
from enum import IntEnum
from typing import Optional

logger = logging.getLogger(__name__)


class DifficultyLevel(IntEnum):
    """Bot difficulty levels, ordered by strength."""
    EASY = 1
    MEDIUM = 2
    HARD = 3
    KHALID = 4  # Expert / Master


# ═══════════════════════════════════════════════════════════════════
# Difficulty Configuration
# ═══════════════════════════════════════════════════════════════════

_DIFFICULTY_CONFIG = {
    DifficultyLevel.EASY: {
        'forget_rate': 0.40,       # 40% chance to "forget" card tracking info
        'random_play_rate': 0.15,  # 15% chance to play a random legal card
        'random_bid_rate': 0.10,   # 10% chance to make suboptimal bid
        'use_endgame': False,      # No minimax endgame solver
        'use_kaboot': False,       # Never actively pursue Kaboot
        'use_brain': False,        # Skip brain cascade (pure heuristics)
        'bid_score_noise': 4,      # +/- 4 random noise on bid evaluation
    },
    DifficultyLevel.MEDIUM: {
        'forget_rate': 0.10,       # 10% memory gaps
        'random_play_rate': 0.08,  # 8% suboptimal plays
        'random_bid_rate': 0.05,   # 5% suboptimal bids
        'use_endgame': False,      # No endgame solver
        'use_kaboot': False,       # Passive Kaboot (don't pursue)
        'use_brain': True,         # Use brain cascade
        'bid_score_noise': 2,      # +/- 2 noise
    },
    DifficultyLevel.HARD: {
        'forget_rate': 0.0,        # Perfect memory
        'random_play_rate': 0.0,   # Always optimal
        'random_bid_rate': 0.0,    # Always optimal
        'use_endgame': True,       # Full minimax
        'use_kaboot': True,        # Active Kaboot pursuit
        'use_brain': True,         # Full brain cascade
        'bid_score_noise': 0,      # No noise
    },
    DifficultyLevel.KHALID: {
        'forget_rate': 0.0,        # Perfect memory
        'random_play_rate': 0.0,   # Always optimal
        'random_bid_rate': 0.0,    # Always optimal
        'use_endgame': True,       # Full minimax + squeeze detection
        'use_kaboot': True,        # Aggressive Kaboot pursuit
        'use_brain': True,         # Full brain cascade
        'bid_score_noise': 0,      # No noise
    },
}


def get_difficulty_config(level: DifficultyLevel) -> dict:
    """Get the config dict for a difficulty level.

    Returns dict with keys: forget_rate, random_play_rate, random_bid_rate,
    use_endgame, use_kaboot, use_brain, bid_score_noise.
    """
    return _DIFFICULTY_CONFIG.get(level, _DIFFICULTY_CONFIG[DifficultyLevel.HARD])


def apply_difficulty_to_play(
    decision: dict,
    level: DifficultyLevel,
    legal_indices: list[int],
) -> dict:
    """Apply difficulty to a PLAY decision.

    May replace the chosen card with a random legal card (for lower difficulties).
    Always returns a valid decision dict.

    Args:
        decision: The bot's chosen play decision (must have 'action' and 'cardIndex').
        level: Current difficulty level.
        legal_indices: List of legal card indices the bot can play.

    Returns:
        Modified decision dict (may have randomized cardIndex).
    """
    if not decision or decision.get('action') != 'PLAY':
        return decision

    config = get_difficulty_config(level)

    # Random play: occasionally pick a random legal card instead of optimal
    if config['random_play_rate'] > 0 and legal_indices:
        if random.random() < config['random_play_rate']:
            original = decision.get('cardIndex')
            random_idx = random.choice(legal_indices)
            if random_idx != original:
                logger.debug(
                    f"[DIFFICULTY] {level.name}: Random play override "
                    f"idx={original} -> {random_idx}"
                )
                decision = {**decision, 'cardIndex': random_idx}
                reason = decision.get('reasoning', '')
                decision['reasoning'] = reason + f" (Difficulty noise: {level.name})"

    return decision


def apply_difficulty_to_bid(
    decision: dict,
    level: DifficultyLevel,
    ctx: Optional[object] = None,
) -> dict:
    """Apply difficulty to a BID decision.

    May convert optimal bids to PASS (for lower difficulties).
    Never converts PASS to a bid (won't make bots bid when they shouldn't).

    Args:
        decision: The bot's chosen bid decision.
        level: Current difficulty level.
        ctx: BotContext (optional, for score-aware noise).

    Returns:
        Modified decision dict (may downgrade to PASS).
    """
    if not decision:
        return decision

    config = get_difficulty_config(level)
    action = decision.get('action', '')

    # Don't downgrade PASS — never force a bid
    if action == 'PASS':
        return decision

    # Random bid degradation: occasionally pass instead of bidding
    if config['random_bid_rate'] > 0:
        if random.random() < config['random_bid_rate']:
            logger.debug(
                f"[DIFFICULTY] {level.name}: Bid downgrade "
                f"{action} -> PASS"
            )
            return {
                'action': 'PASS',
                'reasoning': f"Difficulty noise ({level.name}): missed opportunity"
            }

    return decision


def should_use_endgame(level: DifficultyLevel) -> bool:
    """Whether this difficulty level should use the endgame solver."""
    return get_difficulty_config(level).get('use_endgame', False)


def should_use_kaboot(level: DifficultyLevel) -> bool:
    """Whether this difficulty level should actively pursue Kaboot."""
    return get_difficulty_config(level).get('use_kaboot', False)


def should_use_brain(level: DifficultyLevel) -> bool:
    """Whether this difficulty level should use the brain cascade."""
    return get_difficulty_config(level).get('use_brain', True)


def get_bid_noise(level: DifficultyLevel) -> int:
    """Get random noise to add to bid score evaluation.

    Returns a random integer in range [-noise, +noise].
    """
    noise = get_difficulty_config(level).get('bid_score_noise', 0)
    if noise <= 0:
        return 0
    return random.randint(-noise, noise)


def get_forget_rate(level: DifficultyLevel) -> float:
    """Get the card tracking forget rate for this difficulty."""
    return get_difficulty_config(level).get('forget_rate', 0.0)
