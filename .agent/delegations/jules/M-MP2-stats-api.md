# Jules Task: M-MP2 — Player Stats REST API

## Session Config
```
repo: tazjel/baloot-ai
branch: main
autoApprove: true
autoCreatePR: true
title: [M-MP2] Player stats REST API endpoints
```

## Prompt (copy-paste into Jules)

Create player statistics REST API endpoints for the Baloot AI game server.

The server uses py4web framework. Look at `server/routes/auth.py` for the exact pattern to follow (imports, decorators, bind function).

Create these files:

1. **`server/routes/stats.py`** — New stats routes module with these endpoints:

- `GET /stats/<email>` — Return player statistics (games played, wins, losses, win rate, league points)
  - Query `db.app_user` for user info and `db.game_result` for game history
  - Return 404 if email not found
  - Return JSON: {email, firstName, lastName, gamesPlayed, wins, losses, winRate, leaguePoints}

- `GET /leaderboard` — Return top 50 players sorted by league_points descending
  - Query `db.app_user` ordered by league_points DESC, limit 50
  - Return JSON: {leaderboard: [{rank, firstName, lastName, leaguePoints}, ...]}

- `POST /game-result` — Record a completed game and update league points
  - Accept JSON body: {email, scoreUs, scoreThem, isWin}
  - Insert into `db.game_result` table
  - Update `db.app_user.league_points`: +25 for win, -15 for loss (minimum 0)
  - Return 201 on success, 400 if email missing

- `bind_stats(safe_mount)` function — Binds all routes (same pattern as `bind_auth` in auth.py)

Important: Use these exact imports:
```python
from py4web import action, request, response
from server.common import db
```

2. **`tests/server/test_stats_api.py`** — Unit tests (10+ tests):
- get_player_stats returns 404 for unknown email
- get_player_stats returns correct stats for known player
- get_player_stats returns 0 games for new player with no results
- get_leaderboard returns sorted list by league_points
- get_leaderboard returns max 50 entries
- record_game_result returns 400 when email missing
- record_game_result creates game_result row
- record_game_result updates league_points +25 on win
- record_game_result updates league_points -15 on loss
- record_game_result never lets points go below 0

Use unittest and mock the db object where needed.

Rules:
- DO NOT modify any existing files in server/
- DO NOT modify server/models.py or server/routes/auth.py
- Follow the exact pattern from server/routes/auth.py for decorators and bind function
- Use logging.getLogger(__name__) for the logger
- All functions must have docstrings

When done, create a PR with your changes. Title: "[M-MP2] Player stats REST API endpoints"
