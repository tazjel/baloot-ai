# M-MP9: Server Integration Tests — Jules Task Spec

## Objective
Create a comprehensive integration test suite for the multiplayer server endpoints: authentication, stats, ELO rating, and room management.

## Existing Test Pattern
See `tests/server/test_stats_api.py` for the mocking pattern used in this project. All server tests use `unittest` with mocked `db` objects.

## Server Endpoints to Test

### Auth (`server/routes/auth.py`)
- `POST /signup` — Create account (email, password, first_name, last_name)
- `POST /signin` — Login (email, password) → JWT token
- `GET /validate-token` — Validate JWT token

### Stats (`server/routes/stats.py`)
- `GET /stats/<email>` — Player statistics
- `GET /leaderboard` — Top 50 players
- `POST /game-result` — Record game result

### ELO (`server/routes/elo.py`) — files to be created by M-MP5
- `POST /elo/update` — Update ratings after game
- `GET /elo/rating/<email>` — Get player rating + tier

## Deliverables

### 1. `tests/server/test_auth_integration.py`
Write 12+ tests covering:
- Signup with valid data returns 201
- Signup with missing email returns 400
- Signup with missing password returns 400
- Signup with duplicate email returns 409 (or appropriate error)
- Signin with valid credentials returns JWT token
- Signin with wrong password returns 401
- Signin with non-existent email returns 404
- Token validation with valid token returns 200
- Token validation with expired/invalid token returns 401
- Token validation with missing token returns 400
- Signup then signin flow (full lifecycle)
- JWT token contains expected claims (email, exp)

Use `unittest` and mock the `db` object. Import from `server.routes.auth`.

### 2. `tests/server/test_elo_integration.py`
Write 12+ tests covering:
- `update_elo` with valid winner/loser emails returns new ratings
- `update_elo` winner gains points, loser loses points
- `update_elo` with missing winner_email returns 400
- `update_elo` with missing loser_email returns 400
- `update_elo` with non-existent winner returns 404
- `update_elo` with non-existent loser returns 404
- `update_elo` upset win (weak beats strong) gives more points
- `update_elo` expected win (strong beats weak) gives fewer points
- `get_elo_rating` returns rating and tier for known player
- `get_elo_rating` returns 404 for unknown player
- `get_elo_rating` shows placement status for new player (<10 games)
- `get_elo_rating` shows non-placement for established player (10+ games)

Import from `server.elo_engine` for pure function tests and mock `db` for endpoint tests.

### 3. `tests/server/test_multiplayer_flow.py`
Write 10+ tests covering the full multiplayer flow:
- Signup → signin → get stats (empty) → play game → record result → check stats updated
- Two players: signup both → record game → check ELO updated for both
- Leaderboard returns players sorted by league_points DESC
- Leaderboard limits to 50 entries
- Game result updates league_points correctly
- Multiple games: win streak increases points
- Multiple games: loss streak decreases points (floor at 0)
- Player stats win rate calculation accuracy
- Record game for non-existent user handles gracefully
- ELO placement detection (first 10 games use K=40)

Use `unittest`. Mock the `db` object but test the full function call chains.

## Rules
- DO NOT modify any existing files
- Create ONLY the 3 test files listed above
- Use `unittest` framework (not pytest fixtures)
- Mock `db` using `unittest.mock.patch` and `MagicMock`
- Follow the exact same mocking pattern as `tests/server/test_stats_api.py`
- All tests must be runnable with: `python -m pytest tests/server/ --tb=short -q`
- When done, **create a PR** with title: "[M-MP9] Server integration test suite"
