# Baloot AI — Project Instructions for Claude

## Project Overview
Baloot AI is a full-stack Saudi trick-taking card game with AI bots.
- **Backend**: Python 3.11+ (FastAPI/WebSocket server)
- **Frontend**: React/TypeScript (Vite)
- **AI Worker**: Celery + Redis for async game analysis
- **Game Engine**: Pure Python state machine with Pydantic models

## Architecture

### Game Engine (`game_engine/`)
- `game.py` — Main Game class (Pydantic, stateful)
- `scoring_engine.py` — Point calculation (SUN/HOKUM modes)
- `validation.py` — Move legality checks
- `models/` — Card, Deck, Player, RoundState models

### AI Strategy Layer (`ai_worker/strategies/`)
- `brain.py` — Master orchestrator, `consult_brain()` priority cascade
- `bidding.py` — Bid evaluation (SUN score, HOKUM score, thresholds)
- `components/` — 20+ modular strategy components:
  - `sun.py` / `hokum.py` — Mode-specific play strategies (lead + follow)
  - `lead_selector.py` — 7-strategy cascade for choosing leads
  - `follow_optimizer.py` — 8-tactic cascade for follow plays
  - `endgame_solver.py` — Minimax at ≤3 cards
  - `card_tracker.py` — Card counting and tracking
  - `partner_read.py` — Partner intention inference
  - `trump_manager.py` — Trump management
  - `defense_plan.py` — Defensive play coordination
  - `opponent_model.py` — Opponent threat profiling
  - `trick_review.py` — Mid-round adaptation
  - `cooperative_play.py` — Partner-coordinated plays
  - `hand_shape.py` — Distribution-based bid adjustments

### Bot Context (`ai_worker/bot_context.py`)
The `BotContext` dataclass provides all game state to strategies:
- `hand`, `legal_indices`, `my_seat`, `partner_seat`
- `mode` ("SUN"/"HOKUM"), `trump_suit`, `trump_caller`
- `trick_history`, `current_trick`, `table_cards`
- `round_number`, `team_scores`, `bid_history`

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
logger = logging.getLogger(__name__)

# Constants
ORDER_SUN = ["7","8","9","J","Q","K","10","A"]
ORDER_HOKUM = ["7","8","Q","K","10","A","9","J"]
PTS_SUN = {"A":11,"10":10,"K":4,"Q":3,"J":2}
PTS_HOKUM = {"J":20,"9":14,"A":11,"10":10,"K":4,"Q":3}

def analyze_something(hand, legal_indices, ...) -> dict | None:
    """One-line description.
    
    Returns dict with analysis or None if not applicable.
    """
    # ... logic ...
    return {"recommendation": ..., "confidence": 0.85, "reasoning": "..."}
```

### Integration Points
- **Lead decisions** go in `_get_sun_lead()` / `_get_hokum_lead()`
- **Follow decisions** go in `_get_sun_follow()` / `_get_hokum_follow()`
- **Bidding adjustments** go in `bidding.py` (before threshold checks)
- **Brain cascade** via `brain.py` `consult_brain()` function
- **Always wrap** new module calls in try/except for safety

### Testing
- Tests in `tests/bot/` and `tests/game_logic/`
- Run: `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`
- Current baseline: 37+ bot tests, 300+ total tests

## Task Spec Location
Task specifications for new modules are in `.claude/task_XX_name.md`
Generated code goes to `.claude/staging/` before integration

## What NOT to Do
- Don't modify `game.py` core state machine without explicit approval
- Don't break existing function signatures (add optional params only)
- Don't import between strategy components (they must stay independent)
- Don't use external packages beyond stdlib
- Don't create classes — pure functions only in strategy modules

## Team Workflow
You (Claude MAX) handle complex multi-file refactors, system-level architecture, game-theory strategy design, and full-pipeline integration (module + wiring + tests). 
Gemini (Antigravity) orchestrates, scans gaps, runs tests, and manages the browser/dashboard.
Jules handles parallel simple module generation from specs.
