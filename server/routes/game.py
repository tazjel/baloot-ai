"""
Core game routes: save_score, leaderboard, health_check, catch_all (SPA).
"""
import os
from py4web import action, request, response
from server.common import db
from server.routes.auth import token_required


@action('save_score', method=['POST'])
@token_required
@action.uses(db)
def save_score():
    data = request.json
    score_us = data.get('scoreUs')
    score_them = data.get('scoreThem')
    user_id = request.user.get('user_id')

    user = db.auth_user(user_id)
    if not user:
        response.status = 404
        return {"error": "User not found"}

    db.game_result.insert(
        user_id=user.id,
        score_us=score_us,
        score_them=score_them,
        is_win=(score_us > score_them)
    )

    points_change = 25 if (score_us > score_them) else -15
    new_points = max(0, (user.league_points or 1000) + points_change)
    user.update_record(league_points=new_points)

    return {"message": "Score saved successfully"}


@action('leaderboard', method=['GET'])
@action.uses(db)
def leaderboard():
    top_players = db(db.auth_user).select(orderby=~db.auth_user.league_points, limitby=(0, 10))

    # Safe serialization to avoid exposing password hashes
    leaderboard_data = []
    for p in top_players:
        leaderboard_data.append({
            "first_name": p.first_name,
            "last_name": p.last_name,
            "league_points": p.league_points
        })

    return {"leaderboard": leaderboard_data}


@action('health')
def health_check():
    return "OK"


def catch_all_v2(path=None):
    print("default page being served")
    print(f"DEBUG: catch_all_v2 ENTERED. File: {__file__}", flush=True)
    SERVER_FOLDER = os.path.dirname(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.dirname(SERVER_FOLDER)
    file_path = os.path.join(PROJECT_ROOT, 'static', 'build', 'index.html')

    if not os.path.isfile(file_path):
        return f'File not found: {file_path}', 404

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"DEBUG: catch_all_v2 serving index.html type={type(content)}", flush=True)
        response.headers['Content-Type'] = 'text/html'
        return [content]


def bind_game(safe_mount):
    """Bind game routes to the app."""
    safe_mount('/save_score', 'POST', save_score)
    safe_mount('/leaderboard', 'GET', leaderboard)
    safe_mount('/health', 'GET', health_check)
    # Catch-all must be last
    safe_mount('/', 'GET', catch_all_v2)
    safe_mount('/index', 'GET', catch_all_v2)
    safe_mount('/<path:path>', 'GET', catch_all_v2)
