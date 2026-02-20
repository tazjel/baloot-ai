"""
ELO Rating API endpoints.

- POST /elo/update — Update ratings after a game (accepts winner/loser emails)
- GET /elo/rating/<email> — Get player's current ELO rating and tier
"""
from __future__ import annotations

import logging
from py4web import action, request, response
from server.common import db
from server.elo_engine import (
    calculate_new_rating,
    DEFAULT_RATING,
    PLACEMENT_GAMES,
)

logger = logging.getLogger(__name__)

# Tier thresholds (checked in order, first match wins)
TIERS = [
    (1800, "Grandmaster"),
    (1500, "Master"),
    (1200, "Expert"),
    (900, "Intermediate"),
    (0, "Beginner"),
]


def get_tier(rating: float) -> str:
    """Return tier name based on rating."""
    for threshold, name in TIERS:
        if rating >= threshold:
            return name
    return "Beginner"


@action('elo/update', method=['POST'])
@action.uses(db)
def update_elo():
    """Update ELO ratings after a completed game.

    JSON body:
    {
        "winner_email": "player1@example.com",
        "loser_email": "player2@example.com"
    }

    Both players must exist in app_user.
    Returns new ratings for both players.
    """
    data = request.json
    if not data:
        response.status = 400
        return {"error": "JSON body required"}

    winner_email = data.get('winner_email')
    loser_email = data.get('loser_email')

    if not winner_email or not loser_email:
        response.status = 400
        return {"error": "winner_email and loser_email are required"}

    winner = db(db.app_user.email == winner_email).select().first()
    loser = db(db.app_user.email == loser_email).select().first()

    if not winner:
        response.status = 404
        return {"error": f"Winner not found: {winner_email}"}
    if not loser:
        response.status = 404
        return {"error": f"Loser not found: {loser_email}"}

    # Count games played
    winner_games = db(db.game_result.user_email == winner_email).count()
    loser_games = db(db.game_result.user_email == loser_email).count()

    winner_rating = winner.league_points or DEFAULT_RATING
    loser_rating = loser.league_points or DEFAULT_RATING

    new_winner_rating, winner_change = calculate_new_rating(
        winner_rating, loser_rating, True, winner_games
    )
    new_loser_rating, loser_change = calculate_new_rating(
        loser_rating, winner_rating, False, loser_games
    )

    winner.update_record(league_points=int(new_winner_rating))
    loser.update_record(league_points=int(new_loser_rating))

    return {
        "winner": {
            "email": winner_email,
            "oldRating": winner_rating,
            "newRating": int(new_winner_rating),
            "change": winner_change,
            "tier": get_tier(new_winner_rating),
        },
        "loser": {
            "email": loser_email,
            "oldRating": loser_rating,
            "newRating": int(new_loser_rating),
            "change": loser_change,
            "tier": get_tier(new_loser_rating),
        },
    }


@action('elo/rating/<email>', method=['GET'])
@action.uses(db)
def get_elo_rating(email):
    """Return a player's current ELO rating, tier, and placement status."""
    user = db(db.app_user.email == email).select().first()
    if not user:
        response.status = 404
        return {"error": "Player not found"}

    rating = user.league_points or DEFAULT_RATING
    games_played = db(db.game_result.user_email == email).count()

    return {
        "email": email,
        "rating": rating,
        "tier": get_tier(rating),
        "gamesPlayed": games_played,
        "isPlacement": games_played < PLACEMENT_GAMES,
        "placementGamesRemaining": max(0, PLACEMENT_GAMES - games_played),
    }


def bind_elo(safe_mount):
    """Bind ELO routes to the app."""
    safe_mount('/elo/update', 'POST', update_elo)
    safe_mount('/elo/rating/<email>', 'GET', get_elo_rating)
