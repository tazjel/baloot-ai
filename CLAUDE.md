# Baloot AI — Project Instructions for Claude

## Project Overview
Baloot AI is a full-stack Saudi trick-taking card game with AI bots.
- **Backend**: Python 3.11+ (FastAPI/WebSocket server)
- **Frontend**: React 19/TypeScript (Vite)
- **Mobile**: Flutter/Dart (full game client with Riverpod state management)
- **AI Worker**: Celery + Redis for async game analysis
- **Game Engine**: Pure Python state machine with Pydantic models

## Architecture

### Game Engine (`game_engine/`)

#### Core (`core/`)
- `models.py` — Pydantic base models (Card, Deck, Player)
- `state.py` — RoundState, MatchState immutable state objects
- `rules.py` — Core rule evaluation functions
- `recorder.py` — Game event timeline recording
- `graveyard.py` — Played card tracking

#### Logic (`logic/`)
- `game.py` — Main Game class (Pydantic, stateful) — **DO NOT modify without approval**
- `scoring_engine.py` — Point calculation (SUN/HOKUM modes)
- `game_lifecycle.py` — Round/match lifecycle
- `trick_manager.py` — Trick resolution
- `trick_resolver.py` — Winner determination
- `qayd_engine.py` — Challenge/dispute state machine
- `qayd_state_machine.py` — Qayd FSM transitions
- `qayd_penalties.py` — Qayd penalty calculation
- `bidding_engine.py` — Bid processing
- `contract_handler.py` — Contract enforcement
- `doubling_handler.py` — Double/redouble logic
- `player_manager.py` — Seat/team management
- `project_manager.py` — Mashare3 (projects) management
- `sawa_manager.py` — Sawa detection and scoring
- `akka_manager.py` — Akka detection and scoring
- `baloot_manager.py` — Baloot declaration logic
- `referee.py` — Rule enforcement & validation
- `rules_validator.py` — Card legality checks
- `validation.py` — Input validation layer
- `state_bridge.py` — State format conversion
- `timer_manager.py` — Turn timeout handling
- `autopilot.py` — Auto-play for disconnected players
- `game_serializer.py` — Redis serialization (pickle-safe)
- `utils.py` — Shared utility functions

#### Phases (`logic/phases/`)
- `bidding_phase.py` — Bidding round FSM
- `playing_phase.py` — Trick-taking FSM
- `challenge_phase.py` — Qayd challenge FSM

#### Rules (`logic/rules/`)
- `akka.py` — Akka detection rules
- `projects.py` — Mashare3 detection rules
- `sawa.py` — Sawa detection rules

#### Models (`models/`)
- Card, Deck, Player, RoundState models
- `constants.py` — Canonical game constants (POINT_VALUES, ORDER)

### AI Strategy Layer (`ai_worker/strategies/`)
- `constants.py` — **Shared constants** (ORDER_SUN, ORDER_HOKUM, PTS_SUN, PTS_HOKUM, ALL_SUITS). All strategy modules import from here — NO local constant definitions.
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
- `playing.py` — Play-phase card selection orchestrator
- `sherlock.py` — Deductive card inference engine
- `difficulty.py` — AI difficulty levels
- `neural.py` — Neural network integration layer
- `components/` — **39 modular strategy components**:
  - `sun.py` / `hokum.py` — Mode-specific play strategies (StrategyComponent classes)
  - `sun_bidding.py` / `hokum_bidding.py` — Mode-specific bid evaluation
  - `sun_follow.py` / `hokum_follow.py` — Mode-specific follow logic
  - `sun_defense.py` / `hokum_defense.py` — Mode-specific defense
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
  - `bid_reader.py` / `bid_analysis.py` — Bid inference for play phase
  - `galoss_guard.py` — Emergency mode (losing all tricks)
  - `kaboot_pursuit.py` — Sweep (winning all tricks) pursuit
  - `signaling.py` — Card signaling conventions
  - `trick_projection.py` — Trick count estimation
  - `point_density.py` — Point density classification
  - `doubling_engine.py` — Double decision logic
  - `score_pressure.py` — Score-aware adjustments
  - `lead_preparation.py` — Pre-lead analysis
  - `heuristic_lead.py` — Heuristic fallback leads
  - `discard_logic.py` — Discard optimization
  - `void_trumping.py` — Void-to-trump strategy
  - `personality_filter.py` — Personality-based play filtering
  - `forensics.py` — Post-trick forensic analysis
  - `projects.py` — Mashare3-aware play adjustments
  - `pro_data.py` — Professional play data reference

### AI Subsystems (`ai_worker/`)
- `bot_context.py` — BotContext dataclass (hand, legal_indices, mode, trick_history, etc.)
- `agent.py` — High-level agent orchestrator
- `professor.py` — AI coaching/analysis engine
- `personality.py` — Bot personality traits
- `dialogue_system.py` — Bot chat/taunt generation
- `memory.py` — Short-term card memory
- `memory_hall.py` — Long-term game memory
- `cognitive.py` — Cognitive load modeling
- `llm_client.py` — LLM API integration
- `brain_client.py` — Brain service client
- `mind_client.py` — Mind service client


### Card Objects (`game_engine/models/card.py`)
Cards have `.rank` (str: "7"-"A") and `.suit` (str: "♠","♥","♦","♣")
- **SUN rank order**: 7 < 8 < 9 < J < Q < K < 10 < A
- **HOKUM rank order**: 7 < 8 < Q < K < 10 < A < 9 < J (trump suit)

### Mobile App (`mobile/`)
Flutter/Dart client with Riverpod state management:
- `lib/models/` — Card, Player, GameState data models
- `lib/state/` — Riverpod notifiers and providers (game_state_notifier, action_dispatcher)
- `lib/screens/` — Game board, lobby, settings screens
- `lib/widgets/` — Reusable UI components (card widgets, player panels, modals)
- `lib/services/` — WebSocket, API, storage services
- `lib/utils/` — Shared utilities and helpers

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
- **Python tests** in `tests/bot/` and `tests/game_logic/`
  - Run: `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`
  - Current baseline: **~550 tests passing**
- **Flutter tests** in `mobile/test/`
  - Run: `cd mobile && flutter test`
  - Current baseline: **~138 tests passing**

## What NOT to Do
- Don't modify `game.py` core state machine without explicit approval
- Don't break existing function signatures (add optional params only)
- Don't import between strategy components (they must stay independent)
- Don't use external packages beyond stdlib
- Don't create classes — pure functions only in strategy modules
- Don't define constants locally — import from `ai_worker/strategies/constants.py`

## Team Workflow
- **Claude MAX**: Complex multi-file refactors, system-level architecture, game-theory strategy design, full-pipeline integration (module + wiring + tests)
- **Antigravity (Gemini)**: Orchestration, gap scanning, test running, browser/dashboard management, deep Flutter analysis via MCP, documentation
- **Jules**: Isolated file creation from specs (tests, services, ports). **Always include "create a PR" in prompt text + `autoPr: true`.** See `/jules` workflow for prompt rules and session management.

## Inter-Agent Coordination

### Status Board: `.agent/knowledge/agent_status.md`
- **Check this file** when starting a session for latest status from all agents.
- **Update your section** when you start or complete work.

### Task Delegation
- Claude assigns tasks to Antigravity via `.agent/knowledge/tasks.md`
- Jules tasks use the `/jules` workflow (see above)
- The user triggers handoffs between agents
