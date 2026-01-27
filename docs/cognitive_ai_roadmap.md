# Phase 7: Cognitive AI Roadmap

## Vision
Transform the Baloot AI from a "Competent Heuristic Bot" into a "Superhuman Strategist" capable of long-term planning, bluffing, and perfect endgame execution.

## Core Pillars

### 1. The "Mind's Eye": Probabilistic Hand Estimation
The bot must stop thinking in binaries ("He might have it") and start thinking in distributions.
*   **Technique**: Bayesian Inference or Particle Filtering.
*   **Input**: Bids (Pass = No strong hand), Plays (Did not cover Ace = Likely no King), Signals.
*   **Output**: `P(Card | Player)` matrix.
*   **Application**: "There is a 90% chance Left holds the Ace. I will finesse."

### 2. The "Oracle": Monte Carlo Search (Endgame Solver)
heuristics crumble in complex endgames (squeezes, throw-ins). 
*   **Technique**: Monte Carlo Tree Search (MCTS) / Double Dummy Solver.
*   **Trigger**: When < 5 tricks remain.
*   **Mechanism**:
    1.  Generate 100 random deals for opponents consistent with "Mind's Eye" probabilities.
    2.  Solve each deal to find the move with the highest Win Rate.
    3.  Execute.
*   **Target IQ**: 200+ (Perfect Play).

### 3. The "Psychologist": Strategic Bidding
*   **Sacrifice Bidding**: Bidding to lose small (Khasara) to prevent opponents from winning big (Kaboot/Projects).
*   **Information Bidding**: Bidding to signal strength to partner, not just to buy.
*   **Bluff Detection**: "Opponent bids Sun often on weak hands. I will Double."

## Implementation Plan

### Step 1: Fast Simulation Engine
Create a lightweight `FastGame` class stripped of all server overhead (logs, timers, metadata).
*   **Benchmark**: Must simulate 1,000 tricks/second within Python (or move to Rust/C++ binding if needed).

### Step 2: Perfect Information Solver (Cheater Bot)
Create a bot that sees all cards and uses Minimax/MCTS to play perfectly.
*   **Use**: Generate "Golden Truth" for training and debugging.

### Step 3: Integration
Link `PlayingStrategy` to the Solver. passing the "Most Likely World" to the solver for decision making.

## Metrics for Success
*   **Endgame Win Rate**: % of games won when entering the last 4 tricks with even material.
*   **Project Prevention**: % of times stopping opponent Kaboot.
