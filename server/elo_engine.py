"""
ELO Rating Engine for Baloot AI multiplayer.

Standard ELO with:
- K-factor: 40 for placement (first 10 games), 20 for established players
- Floor rating: 100 (never go below)
- Starting rating: 1000
"""
from __future__ import annotations

import math
import logging

logger = logging.getLogger(__name__)

DEFAULT_RATING = 1000
RATING_FLOOR = 100
K_PLACEMENT = 40  # First 10 games
K_ESTABLISHED = 20  # After 10 games
PLACEMENT_GAMES = 10


def expected_score(rating_a: float, rating_b: float) -> float:
    """Calculate expected score for player A against player B.

    Returns float between 0 and 1.
    """
    return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))


def get_k_factor(games_played: int) -> int:
    """Return K-factor based on number of games played.

    Higher K during placement for faster convergence.
    """
    if games_played < PLACEMENT_GAMES:
        return K_PLACEMENT
    return K_ESTABLISHED


def calculate_new_rating(
    player_rating: float,
    opponent_rating: float,
    player_won: bool,
    player_games: int,
) -> tuple[float, float]:
    """Calculate new ELO rating after a game.

    Args:
        player_rating: Current rating of the player.
        opponent_rating: Current rating of the opponent.
        player_won: True if player won, False if lost.
        player_games: Number of games the player has completed.

    Returns:
        Tuple of (new_rating, rating_change).
    """
    expected = expected_score(player_rating, opponent_rating)
    actual = 1.0 if player_won else 0.0
    k = get_k_factor(player_games)
    change = k * (actual - expected)
    new_rating = max(RATING_FLOOR, player_rating + change)
    return (round(new_rating, 1), round(change, 1))


def calculate_team_rating(ratings: list[float]) -> float:
    """Calculate average rating for a team (2 players in Baloot).

    Returns average of the team members' ratings.
    """
    if not ratings:
        return DEFAULT_RATING
    return sum(ratings) / len(ratings)
