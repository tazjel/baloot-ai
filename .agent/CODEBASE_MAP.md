# Codebase Map

## High-Level Structure

```
baloot-ai/
├── ai_worker/              # AI "Brain" — strategy + analysis
│   ├── bot_context.py      # BotContext: typed game state wrapper
│   ├── memory.py           # CardMemory: Bayesian suit probabilities + card tracking
│   ├── agent.py            # Main AI entry point
│   ├── mcts/               # Monte Carlo Tree Search
│   │   ├── fast_game.py    # Lightweight game simulation
│   │   └── utils.py        # MCTS utilities + Bayesian weighting
│   └── strategies/
│       ├── constants.py    # ★ SHARED CONSTANTS — all modules import from here
│       ├── bidding.py      # Bid evaluation (SUN/HOKUM scoring)
│       ├── playing.py      # Play orchestration entry point
│       └── components/     # 26+ modular strategy modules
│           ├── brain.py        # ★ 7-step priority cascade orchestrator
│           ├── sun.py          # SUN mode strategy (StrategyComponent class)
│           ├── hokum.py        # HOKUM mode strategy (StrategyComponent class)
│           ├── lead_selector.py    # 7-strategy lead cascade
│           ├── follow_optimizer.py # 8-tactic follow cascade
│           ├── opponent_model.py   # Opponent threat profiling → brain step 4
│           ├── trick_review.py     # Momentum detection → brain threshold
│           ├── endgame_solver.py   # Minimax at ≤3 cards
│           ├── card_tracker.py     # Card counting
│           ├── partner_read.py     # Partner inference
│           ├── trump_manager.py    # HOKUM trump strategy
│           ├── defense_plan.py     # Defensive play
│           ├── cooperative_play.py # Partner coordination
│           ├── hand_shape.py       # Distribution analysis
│           ├── bid_reader.py       # Bid inference for play
│           ├── galoss_guard.py     # Emergency mode (losing all)
│           ├── kaboot_pursuit.py   # Sweep pursuit (winning all)
│           ├── signaling.py        # Card signaling
│           ├── trick_projection.py # Trick count estimation
│           └── point_density.py    # Point density classification
├── frontend/               # React 19 + Vite application
│   └── src/
│       ├── App.tsx         # Main app with routing
│       ├── components/     # UI components
│       │   ├── table/      # Game table (GameArena, PlayerAvatar)
│       │   ├── dispute/    # Dispute resolution
│       │   ├── effects/    # Visual effects
│       │   └── overlays/   # Game overlays
│       ├── hooks/          # React hooks (useRoundManager, useGameSocket, etc.)
│       ├── services/       # API, Socket, AccountingEngine
│       └── types.ts        # TypeScript type definitions
├── game_engine/            # Core Python game logic
│   ├── logic/
│   │   ├── game.py         # ★ Main Game state machine (DO NOT modify without approval)
│   │   ├── game_lifecycle.py   # Round/match lifecycle
│   │   ├── scoring_engine.py   # Point calculation
│   │   ├── trick_manager.py    # Trick rules and flow
│   │   ├── qayd_engine.py      # Challenge/dispute state machine
│   │   ├── project_manager.py  # Mashrou (declarations) detection
│   │   └── phases/             # Phase implementations (Bidding, Playing, Challenge)
│   └── models/
│       ├── card.py         # Card model (.rank, .suit)
│       ├── constants.py    # Game-level constants (POINT_VALUES, ORDER)
│       └── ...             # Deck, Player, RoundState
├── server/                 # Flask + Socket.IO Backend
│   ├── socket_handler.py   # Real-time event handling + CORS
│   ├── room_manager.py     # Room lifecycle (MAX_ROOMS=500, sid tracking)
│   ├── rate_limiter.py     # Redis + in-memory fallback
│   ├── auth_utils.py       # JWT with secret validation
│   └── handlers/           # Event handlers (game_actions, room_lifecycle, telemetry)
├── tests/                  # 332+ tests
│   ├── bot/                # AI strategy tests
│   └── game_logic/         # Game engine tests
└── .agent/                 # Agent configuration
    ├── knowledge/          # Glossary, rulebook, developer tips
    ├── workflows/          # Agent workflows
    └── skills/             # Agent skills
```

## Key Mechanisms
- **Phase State Pattern**: `Game` delegates to `phases/` modules based on `self.phase`
- **Brain Cascade**: 7-step priority with dynamic threshold from trick_review momentum
- **Bayesian Integration**: CardMemory suit_probability feeds lead_selector + follow_optimizer
- **Strategy Independence**: Components NEVER import each other; brain.py orchestrates
- **Constants Single Source**: `ai_worker/strategies/constants.py` — no local duplicates
- **Qayd (Forensic Mode)**: Handled by `ChallengePhase` + `QaydManager`
- **AI Worker**: Runs as separate process, communicating via Redis/Socket.IO
