# M-MP5: ELO Rating Engine — Jules Task Spec

## Objective
Create an ELO rating engine module and REST API endpoint for the Baloot AI multiplayer server. This replaces the current flat +25/-15 league points system with proper ELO-based skill ratings.

## Deliverables

### 1. `server/elo_engine.py` — Pure ELO calculation module

```python
"""
ELO Rating Engine for Baloot AI multiplayer.

Standard ELO with:
- K-factor: 40 for placement (first 10 games), 20 for established players
- Floor rating: 100 (never go below)
- Starting rating: 1000
"""
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
        player_rating: Current rating of the player
        opponent_rating: Current rating of the opponent
        player_won: True if player won, False if lost
        player_games: Number of games the player has completed

    Returns:
        Tuple of (new_rating, rating_change)
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
```

### 2. `server/routes/elo.py` — ELO API endpoints

```python
"""
ELO Rating API endpoints.
- POST /elo/update — Update ratings after a game (accepts team results)
- GET /elo/rating/<email> — Get player's current ELO rating and tier
"""
import logging
from py4web import action, request, response
from server.common import db
from server.elo_engine import (
    calculate_new_rating,
    DEFAULT_RATING,
    PLACEMENT_GAMES,
)

logger = logging.getLogger(__name__)

# Tier thresholds
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
    """
    Update ELO ratings after a completed game.

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
```

### 3. `tests/server/test_elo_engine.py` — Unit tests (15+ tests)

Write tests covering:
- `expected_score` returns 0.5 for equal ratings
- `expected_score` returns >0.5 when player A is stronger
- `expected_score` returns <0.5 when player A is weaker
- `get_k_factor` returns 40 for placement (0-9 games)
- `get_k_factor` returns 20 for established (10+ games)
- `calculate_new_rating` winner gains points
- `calculate_new_rating` loser loses points
- `calculate_new_rating` upset win gives more points (weak beats strong)
- `calculate_new_rating` expected win gives fewer points (strong beats weak)
- `calculate_new_rating` rating never goes below RATING_FLOOR (100)
- `calculate_new_rating` placement K-factor gives larger changes
- `calculate_team_rating` averages correctly
- `calculate_team_rating` returns DEFAULT_RATING for empty list
- `get_tier` returns correct tier for each threshold
- `update_elo` endpoint returns 400 without emails
- `update_elo` endpoint returns 404 for unknown player

Use `unittest` and mock the `db` object for endpoint tests. Import from `server.elo_engine` for pure function tests.

## Rules
- DO NOT modify any existing files (no changes to stats.py, models.py, auth.py, etc.)
- Create ONLY the 3 files listed above
- Follow the exact function signatures shown
- Use `py4web` decorators matching the existing `stats.py` pattern
- The `bind_elo` function follows the same pattern as `bind_stats` in stats.py
- When done, **create a PR** with title: "[M-MP5] ELO Rating Engine"
