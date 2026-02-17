# Baloot AI — Project Instructions for Claude

## Project Overview
Baloot AI is a full-stack Saudi trick-taking card game with AI bots.
- **Backend**: Python 3.11+ (FastAPI/WebSocket server)
- **Frontend**: React 19/TypeScript (Vite)
- **AI Worker**: Celery + Redis for async game analysis
- **Game Engine**: Pure Python state machine with Pydantic models

## Architecture

### Game Engine (`game_engine/`)
- `game.py` — Main Game class (Pydantic, stateful) — DO NOT modify without approval
- `logic/scoring_engine.py` — Point calculation (SUN/HOKUM modes)
- `logic/game_lifecycle.py` — Round/match lifecycle
- `logic/trick_manager.py` — Trick resolution
- `logic/qayd_engine.py` — Challenge/dispute state machine
- `models/` — Card, Deck, Player, RoundState models
- `models/constants.py` — Canonical game constants (POINT_VALUES, ORDER)

### AI Strategy Layer (`ai_worker/strategies/`)
- `constants.py` — **Shared constants** (ORDER_SUN, ORDER_HOKUM, PTS_SUN, PTS_HOKUM, ALL_SUITS, scoring totals). All strategy modules import from here — NO local constant definitions.
- `brain.py` — Master orchestrator, `consult_brain()` 7-step priority cascade:
  1. Kaboot Pursuit — sweep override
  2. Point Density — trick value assessment
  3. Trump Manager — HOKUM lead strategy
  4. Opponent Model — avoid dangerous suits, prefer safe leads
  5. Defense Plan — defender lead guidance
  6. Partner Signal — lead toward partner strength
  7. Default — yield to existing heuristics
  - Dynamic threshold (0.4–0.6) adjusted by trick_review momentum
  - Accepts `opponent_info` and `trick_review_info` from callers
- `bidding.py` — Bid evaluation (SUN score, HOKUM score, thresholds)
- `components/` — 26+ modular strategy components:
  - `sun.py` / `hokum.py` — Mode-specific play strategies (StrategyComponent classes)
  - `lead_selector.py` — 7-strategy cascade (supports Bayesian suit_probs)
  - `follow_optimizer.py` — 8-tactic cascade (supports Bayesian suit_probs)
  - `endgame_solver.py` — Minimax at ≤3 cards
  - `card_tracker.py` — Card counting and tracking
  - `partner_read.py` — Partner intention inference
  - `trump_manager.py` — Trump management (HOKUM)
  - `defense_plan.py` — Defensive play coordination
  - `opponent_model.py` — Opponent threat profiling → feeds brain cascade
  - `trick_review.py` — Mid-round momentum/shift → adjusts brain threshold
  - `cooperative_play.py` — Partner-coordinated plays
  - `hand_shape.py` — Distribution-based bid adjustments
  - `bid_reader.py` — Bid inference for play phase
  - `galoss_guard.py` — Emergency mode (losing all tricks)
  - `kaboot_pursuit.py` — Sweep (winning all tricks) pursuit
  - `signaling.py` — Card signaling conventions
  - `trick_projection.py` — Trick count estimation
  - `point_density.py` — Point density classification

### Bot Context (`ai_worker/bot_context.py`)
The `BotContext` dataclass provides all game state to strategies:
- `hand`, `legal_indices`, `my_seat`, `partner_seat`
- `mode` ("SUN"/"HOKUM"), `trump_suit`, `trump_caller`
- `trick_history`, `current_trick`, `table_cards`
- `round_number`, `team_scores`, `bid_history`
- `memory` — CardMemory with Bayesian suit probabilities
- `is_partner_winning()`, `is_master_card()`, `is_player_void()`

### Card Objects (`game_engine/models/card.py`)
Cards have `.rank` (str: "7"-"A") and `.suit` (str: "♠","♥","♦","♣")
- **SUN rank order**: 7 < 8 < 9 < J < Q < K < 10 < A
- **HOKUM rank order**: 7 < 8 < Q < K < 10 < A < 9 < J (trump suit)

## Conventions

### Code Style
- Pure functions preferred for strategy modules (no classes)
- `from __future__ import annotations` at top of every file
- Docstrings on all public functions
- Type hints on function signatures
- `logging.getLogger(__name__)` for debug output
- Try/except wrapping when integrating new modules (fail-safe)

### Strategy Module Pattern
Every module in `components/` follows this pattern:
```python
from __future__ import annotations
import logging
from ai_worker.strategies.constants import ORDER_SUN, ORDER_HOKUM, PTS_SUN, PTS_HOKUM

logger = logging.getLogger(__name__)

def analyze_something(hand, legal_indices, ...) -> dict | None:
    """One-line description.

    Returns dict with analysis or None if not applicable.
    """
    # ... logic ...
    return {"recommendation": ..., "confidence": 0.85, "reasoning": "..."}
```

### Integration Points
- **Lead decisions** go through `lead_selector.select_lead()` (called from sun.py/hokum.py)
- **Follow decisions** go through `follow_optimizer.optimize_follow()` (called from sun.py/hokum.py)
- **Bidding adjustments** go in `bidding.py` (before threshold checks)
- **Brain cascade** via `brain.py` `consult_brain()` — add new steps as optional params
- **trick_review + opponent_model** are computed BEFORE brain in sun.py/hokum.py, passed as params
- **Always wrap** new module calls in try/except for safety

### Testing
- Tests in `tests/bot/` and `tests/game_logic/`
- Run: `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`
- Current baseline: **332 tests passing** (as of Mission 15)
- Some integration tests need `game.strictMode = False` to play arbitrary cards

## What NOT to Do
- Don't modify `game.py` core state machine without explicit approval
- Don't break existing function signatures (add optional params only)
- Don't import between strategy components (they must stay independent)
- Don't use external packages beyond stdlib
- Don't create classes — pure functions only in strategy modules
- Don't define constants locally — import from `ai_worker/strategies/constants.py`

## Team Workflow
You (Claude MAX) handle complex multi-file refactors, system-level architecture, game-theory strategy design, and full-pipeline integration (module + wiring + tests).
Gemini (Antigravity) orchestrates, scans gaps, runs tests, manages the browser/dashboard, and **performs deep Flutter analysis via MCP**.
Jules handles parallel simple module generation from specs.
