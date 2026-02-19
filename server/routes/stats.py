import logging
from py4web import action, request, response
from server.common import db

logger = logging.getLogger(__name__)

@action('stats/<email>', method=['GET'])
@action.uses(db)
def get_player_stats(email):
    """
    Return player statistics for the given email.
    Queries db.app_user for user info and db.game_result for game history.
    """
    user = db(db.app_user.email == email).select().first()
    if not user:
        response.status = 404
        return {"error": "User not found"}

    games = db(db.game_result.user_email == email).select()
    games_played = len(games)
    wins = len([g for g in games if g.is_win])
    losses = games_played - wins
    win_rate = (wins / games_played * 100) if games_played > 0 else 0

    return {
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "gamesPlayed": games_played,
        "wins": wins,
        "losses": losses,
        "winRate": win_rate,
        "leaguePoints": user.league_points
    }

@action('leaderboard', method=['GET'])
@action.uses(db)
def get_leaderboard():
    """
    Return top 50 players sorted by league_points descending.
    Queries db.app_user ordered by league_points DESC, limit 50.
    """
    users = db().select(
        db.app_user.ALL,
        orderby=~db.app_user.league_points,
        limitby=(0, 50)
    )

    leaderboard = []
    for i, user in enumerate(users):
        leaderboard.append({
            "rank": i + 1,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "leaguePoints": user.league_points
        })

    return {"leaderboard": leaderboard}

@action('game-result', method=['POST'])
@action.uses(db)
def record_game_result():
    """
    Record a completed game and update league points.
    Accepts JSON body with email, scoreUs, scoreThem, isWin.
    """
    data = request.json
    if not data or 'email' not in data:
        response.status = 400
        return {"error": "Email is required"}

    email = data.get('email')
    score_us = data.get('scoreUs')
    score_them = data.get('scoreThem')
    is_win = data.get('isWin')

    db.game_result.insert(
        user_email=email,
        score_us=score_us,
        score_them=score_them,
        is_win=is_win
    )

    user = db(db.app_user.email == email).select().first()
    if user:
        # Update league points: +25 for win, -15 for loss (minimum 0)
        points_change = 25 if is_win else -15
        new_points = max(0, user.league_points + points_change)
        user.update_record(league_points=new_points)

    response.status = 201
    return {"message": "Game result recorded successfully"}

def bind_stats(safe_mount):
    """
    Binds all stats routes to the app.
    Same pattern as bind_auth in auth.py.
    """
    safe_mount('/stats/<email>', 'GET', get_player_stats)
    safe_mount('/leaderboard', 'GET', get_leaderboard)
    safe_mount('/game-result', 'POST', record_game_result)
