# Active Task Distribution — 2026-02-20 (Multiplayer Phase)

> **Phase**: MP (Multiplayer Production) | **Wave**: A (Identity & Server)
> **Flutter M-F1→20**: ✅ All Done | **MP-1/2**: 🔄 Jules | **QA**: ⏳ Antigravity

---

## Jules — M-MP1: Server Dockerfile + Deploy Config

### Objective
Create a production-ready Dockerfile for the Python backend server and update docker-compose.yml.

### Deliverables
Create these files:

1. **`Dockerfile`** (project root)
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   ENV PYTHONUNBUFFERED=1
   ENV BALOOT_ENV=production
   EXPOSE 3005
   CMD ["python", "-m", "server.main"]
   ```

2. **`server/.env.example`** — Environment template
   ```
   BALOOT_ENV=production
   JWT_SECRET=<generate-a-real-secret>
   REDIS_URL=redis://redis:6379/0
   CORS_ORIGINS=https://baloot-ai.com
   MAX_ROOMS=500
   BOT_DELAY_MS=1500
   ```

3. **Update `docker-compose.yml`** — Add server service:
   ```yaml
   server:
     build: .
     ports:
       - "3005:3005"
     environment:
       - REDIS_URL=redis://redis:6379/0
       - BALOOT_ENV=production
     depends_on:
       redis:
         condition: service_healthy
     networks:
       - baloot_net
   ```

4. **`.dockerignore`** (project root)
   ```
   .git
   .agent
   .claude
   mobile/
   frontend/node_modules
   __pycache__
   *.pyc
   .env
   ```

### Rules
- DO NOT modify `server/main.py`, `server/application.py`, or any existing Python files
- DO NOT modify `server/settings.py` (it already reads env vars)
- The Dockerfile must use `python:3.12-slim` base image
- The docker-compose update must KEEP the existing redis + redis-ui services intact
- When done, create a PR with your changes. Title: "[M-MP1] Server Dockerfile and deploy config"

---

## Jules — M-MP2: Player Stats REST API

### Objective
Add REST API endpoints for player statistics, leaderboard, and game result recording.

### Deliverables
Create this file:

1. **`server/routes/stats.py`** — New stats routes module

```python
"""
Player statistics API endpoints.
- GET /stats/<email> — player stats (wins, losses, win rate, league points)
- GET /leaderboard — top 50 players by league points
- POST /game-result — record a completed game result
"""
from py4web import action, request, response
from server.common import db
import datetime
import logging

logger = logging.getLogger(__name__)


@action('stats/<email>', method=['GET'])
def get_player_stats(email):
    """Return player statistics: games played, wins, losses, win rate, league points."""
    user = db(db.app_user.email == email).select().first()
    if not user:
        response.status = 404
        return {"error": "Player not found"}

    results = db(db.game_result.user_email == email).select()
    total = len(results)
    wins = sum(1 for r in results if r.is_win)
    losses = total - wins
    win_rate = round(wins / total * 100, 1) if total > 0 else 0.0

    return {
        "email": email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "gamesPlayed": total,
        "wins": wins,
        "losses": losses,
        "winRate": win_rate,
        "leaguePoints": user.league_points or 1000,
    }


@action('leaderboard', method=['GET'])
def get_leaderboard():
    """Return top 50 players sorted by league points descending."""
    players = db(db.app_user.id > 0).select(
        db.app_user.first_name, db.app_user.last_name,
        db.app_user.email, db.app_user.league_points,
        orderby=~db.app_user.league_points,
        limitby=(0, 50)
    )
    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "firstName": p.first_name,
                "lastName": p.last_name,
                "leaguePoints": p.league_points or 1000,
            }
            for i, p in enumerate(players)
        ]
    }


@action('game-result', method=['POST'])
@action.uses(db)
def record_game_result():
    """Record a completed game result and update league points."""
    data = request.json
    email = data.get('email')
    score_us = data.get('scoreUs', 0)
    score_them = data.get('scoreThem', 0)
    is_win = data.get('isWin', False)

    if not email:
        response.status = 400
        return {"error": "email is required"}

    db.game_result.insert(
        user_email=email,
        score_us=score_us,
        score_them=score_them,
        is_win=is_win,
        timestamp=datetime.datetime.now()
    )

    # Update league points: +25 for win, -15 for loss (min 0)
    user = db(db.app_user.email == email).select().first()
    if user:
        delta = 25 if is_win else -15
        new_points = max(0, (user.league_points or 1000) + delta)
        user.update_record(league_points=new_points)

    db.commit()
    response.status = 201
    return {"message": "Game result recorded", "pointsDelta": delta if user else 0}


def bind_stats(safe_mount):
    """Bind stats routes to the app."""
    safe_mount('/stats/<email>', 'GET', get_player_stats)
    safe_mount('/leaderboard', 'GET', get_leaderboard)
    safe_mount('/game-result', 'POST', record_game_result)
```

2. **`tests/server/test_stats_api.py`** — Unit tests

Write 10+ tests covering:
- `get_player_stats` returns 404 for unknown email
- `get_player_stats` returns correct win/loss/rate for known player
- `get_player_stats` returns 0 games for new player
- `get_leaderboard` returns sorted list
- `get_leaderboard` returns max 50 entries
- `record_game_result` requires email field
- `record_game_result` creates game_result row
- `record_game_result` updates league_points on win (+25)
- `record_game_result` updates league_points on loss (-15)
- `record_game_result` never goes below 0 points

Use `unittest` and mock the `db` object. Import from `server.routes.stats`.

### Rules
- DO NOT modify any existing files in `server/`
- DO NOT modify `server/models.py` or `server/routes/auth.py`
- Follow the exact function signatures and `bind_stats` pattern shown above
- Use `py4web` decorators matching the existing auth.py pattern
- When done, create a PR with your changes. Title: "[M-MP2] Player stats REST API endpoints"

---

## Antigravity — QA Tasks (after Jules PRs arrive)

### 🔴 QA-MP1: Docker Build Verification
```powershell
git pull origin main
# Or checkout the Jules PR branch
docker build -t baloot-server .
docker compose up -d
# Wait 10s for startup
curl http://localhost:3005/health  # Should return 200
docker compose down
```

**Report**: Does it build? Does the server start? Any errors in logs?

### 🔴 QA-MP2: Stats API Smoke Test
```powershell
# Start server (docker or manual)
# Test stats endpoint
curl http://localhost:3005/stats/test@example.com
# Expected: 404 {"error": "Player not found"}

curl http://localhost:3005/leaderboard
# Expected: 200 {"leaderboard": [...]}

curl -X POST http://localhost:3005/game-result \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "scoreUs": 152, "scoreThem": 100, "isWin": true}'
# Expected: 201 or 400 if user doesn't exist
```

**Report**: Do endpoints respond correctly? Any 500 errors?

### 🟡 QA-Baseline: Regression Check
```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
flutter test
flutter analyze
```

**Report**: Still 151 tests passing? 0 errors in analyze?

### Report Template
Post results in `agent_status.md` under "Antigravity Results":
```
### QA-MP1: Docker Build
- Build: ✅/❌
- Server start: ✅/❌
- Errors: (paste any)

### QA-MP2: Stats API
- GET /stats/unknown: ✅ 404 / ❌
- GET /leaderboard: ✅ 200 / ❌
- POST /game-result: ✅ 201 / ❌
- Errors: (paste any)

### QA-Baseline
- Flutter tests: X passing
- Flutter analyze: X errors
```

---

## Claude MAX — Queued (after Phase A delivers)

### M-MP3: Flutter Auth Flow
- Login screen (email + password)
- Signup screen (name + email + password)
- Guest mode (skip auth, local-only stats)
- JWT token persistence (flutter_secure_storage)
- Auth state provider (Riverpod)
- Protected routes (redirect to login if no token)
- Wire player name from auth into multiplayer

### M-MP4: Session Recovery
- Store active room ID + player index in secure storage
- On app restart, attempt rejoin with stored credentials
- Show "Reconnecting..." overlay during recovery
- If room expired, show "Game ended" dialog

---

## File Locks
- `server/routes/stats.py` — LOCKED by Jules (M-MP2)
- `Dockerfile` — LOCKED by Jules (M-MP1)
- `docker-compose.yml` — LOCKED by Jules (M-MP1)
