# Milestone: Kammelna Engine Reverse-Engineering

> **Priority**: 🔴 HIGHEST — Must complete before game theory enhancements
> **Data Source**: 109 professional games in `gbaloot/data/archive_captures/mobile_export/savedGames/*.json`
> **Schema**: `gbaloot/data/KAMMELNA_SCHEMA.md` (1,172 lines, verified)
> **Output**: All scripts go in `scripts/reverse_engineering/`, all data outputs go in `gbaloot/data/training/`

---

## Mission 1: Event State Machine Extraction

**Goal**: Map the complete game engine FSM — every legal event transition.

### Tasks

1. **Parse all 109 games** and extract every `(event_type, next_event_type)` transition pair
2. **Build a transition matrix**: For each event type `e=X`, what event types can follow it?
3. **Identify mandatory sequences**: e.g., `e=15 → e=1` (deal always precedes start)
4. **Document conditional branches**: When does `e=3` (declaration) appear mid-trick vs between tricks?
5. **Count transition frequencies**: How often does each transition occur?
6. **Generate a Mermaid state diagram** of the complete engine lifecycle

### Output: `gbaloot/data/training/event_state_machine.json`
```python
{
    "transitions": {
        "15→1": {"count": 1629, "note": "Deal → Round Start (100% mandatory)"},
        "1→2": {"count": 1629, "note": "Round Start → First Bid (100%)"},
        "2→2": {"count": 10662, "note": "Bid → Bid (bidding sequence)"},
        "2→4": {"count": 946, "note": "Bid → Card Play (bidding complete)"},
        "4→4": {"count": 8200, "note": "Card → Card (within trick)"},
        "4→6": {"count": 7568, "note": "Card → Trick Won (4th card triggers)"},
        "6→4": {"count": 6622, "note": "Trick Won → Next Lead"},
        "4→3": {"count": ..., "note": "Card → Declaration (mid-play)"},
        "3→4": {"count": ..., "note": "Declaration → Card Play"},
        ...
    },
    "event_types": {1: "Round Start", 2: "Bid", 3: "Declaration", 4: "Card Play", 
                    5: "Foul", 6: "Trick Won", 7: "Challenge", 8: "Chat",
                    9: "Session Resume", 10: "Disconnect", 11: "Rejoin",
                    12: "Round Result", 15: "Deal", 16: "Kawesh"},
    "mandatory_sequences": ["15→1→2", "4→4→4→4→6"],
    "mermaid_diagram": "..."
}
```

### Script: `scripts/reverse_engineering/extract_state_machine.py`

---

## Mission 2: Human vs AI Move Labeling

**Goal**: For every card played and bid made, label it as HUMAN, AUTOPLAY, or BOT.

### Background
- **AUTOPLAY**: When a human player doesn't act within 5 seconds, Kammelna's AI auto-plays for them
- **BOT**: When a player disconnects (`e=10`), Kammelna's AI takes over entirely until reconnect (`e=11`)
- **HUMAN**: Normal human play

### Tasks

1. **Find all disconnect/rejoin windows**: Scan for `e=10` (disconnect) and `e=11` (rejoin) events
   - All moves between disconnect and rejoin are BOT moves
   - If no rejoin happens, all remaining moves in that round are BOT
2. **Tag every event with player type**: Add `"player_type": "HUMAN" | "BOT" | "UNKNOWN"` 
3. **Cross-reference with GBoard timing** (when available): If a card was played at exactly 5.0s after the previous event, tag as AUTOPLAY
4. **Build statistics**:
   - How many moves are BOT? What % of total?
   - Which player seats get BOT more often?
   - Do BOT moves correlate with losing?
5. **Detect patterns in Kammelna's bot behavior**:
   - Does the bot always play the highest legal card? The lowest?
   - Does the bot trump when possible?
   - Does the bot bid conservatively or aggressively?

### Output: `gbaloot/data/training/move_labels.json`
```python
{
    "labeled_moves": [
        {
            "game": "جلسة 1280",
            "round": 16,
            "event_idx": 9,
            "event_type": 4,  # card play
            "player": 3,
            "player_type": "BOT",  # Between e=10 and e=11
            "card": 25,
            "context": "disconnect_window"
        },
        ...
    ],
    "statistics": {
        "total_moves": 14000,
        "human_moves": 13200,
        "bot_moves": 450,
        "autoplay_moves": 350,  # From GBoard timing only
        "bot_move_percentage": 3.2
    }
}
```

### Script: `scripts/reverse_engineering/label_player_types.py`

---

## Mission 3: Kammelna AI Benchmarking

**Goal**: Evaluate how strong Kammelna's autoplay/bot AI actually is.

### Prerequisites
- Mission 2 completed (move labels available)
- Mission 1 completed (state machine available)

### Tasks

1. **Extract all BOT card play decisions** with full game context:
   - What hand did the bot have? (from `bhr` bitmask)
   - What were the legal moves? (reconstruct from game state)
   - What did the bot choose?
   - Was it the trick leader or follower?
   - Did the bot win the trick?

2. **Evaluate bot bidding**:
   - When the bot bids (during disconnect windows), what does it bid?
   - Compare hand strength at bid time vs bid choice
   - Does the bot ever bid Sun? Ashkal?

3. **Compare bot vs human play on equivalent situations**:
   - Find situations where both a human and a bot faced similar hands
   - Did they choose the same card?
   - Who won more tricks/points?

4. **Score the bot's play quality**:
   - **Point efficiency**: Average points per trick (bot vs human)
   - **Trick win rate**: % of tricks won (bot vs human)
   - **Khasara rate**: % of rounds lost by bot's team when bot was playing

5. **Document the bot's strategy**:
   - Does the bot lead with aces?
   - Does the bot trump immediately or hold trump?
   - Does the bot discard high cards or low cards?
   - Does the bot handle endgame (last 2-3 tricks) differently?

### Output: `gbaloot/data/training/kammelna_ai_benchmark.json`

### Script: `scripts/reverse_engineering/benchmark_kammelna_ai.py`

---

## Mission 4: Declaration & Project System Analysis

**Goal**: Fully document when and how declarations (projects/mashru3) are triggered, validated, and scored.

### Tasks

1. **Map declaration timing**:
   - Extract all `e=3` events and their position relative to card plays
   - When does `prj` (type announcement) appear vs `prjC` (card proof)?
   - Are declarations always before the first card? Or can they come later?

2. **Declaration priority resolution**:
   - When both teams declare in the same round, which takes priority?
   - Extract all rounds with competing declarations and verify who gets credit

3. **Baloot (King+Queen of trump) specifics**:
   - When is Baloot declared (`prj=6`)?
   - Is it auto-detected or player-chosen?
   - What happens to Baloot on Khasara? On Qahwa?

4. **Validate our engine's declaration logic**:
   - Compare `e=3` events from archives against our `scoring_engine.py` logic
   - Find any mismatches in declaration values or timing

### Output: `gbaloot/data/training/declaration_analysis.json`

### Script: `scripts/reverse_engineering/analyze_declarations.py`

---

## Mission 5: Trick Resolution & Card Hierarchy

**Goal**: Empirically verify every trick's winner against our trick resolution logic.

### Tasks

1. **Reconstruct all ~7,568 tricks** from the 109 games:
   - For each trick: 4 cards played (from `e=4`), winner (from `e=6`), game mode, trump suit
   - Note: `e=6.p` = winner's seat

2. **Verify our `trick_resolver.py`**:
   - Feed each trick's 4 cards + game mode + trump into our resolver
   - Compare our predicted winner vs archive's `e=6.p`
   - Target: 100% agreement

3. **Build card hierarchy table**:
   - In Sun: what beats what? (standard rank order)
   - In Hokm: trump order vs non-trump order
   - Verify J and 9 of trump are highest (J=20pts, 9=14pts)

4. **Edge cases**:
   - What happens when two players play the same rank card of non-trump?
   - Who wins when no one follows suit and no trump is played?
   - Verify lead-suit advantage (first card's suit must be followed)

### Output: `gbaloot/data/training/trick_resolution_verify.json`

### Script: `scripts/reverse_engineering/verify_tricks.py`

---

## Mission 6: Scoring Pipeline Verification (Extended)

**Goal**: Extend the 100% GP verification to cover ALL edge cases and produce reproducible scoring formulas.

### Tasks

1. **Verify all 946 contracted rounds** produce the exact GP shown in `e=12.rs`:
   - Raw points (`p1`, `p2`)
   - Effective points (`e1`, `e2`) — after declarations
   - Game points (`s1`, `s2`) — after GP conversion
   - Already 100% verified, but reproduce with a reusable script

2. **Document the effective points formula**:
   - `effective = raw + own_declarations - opponent_declarations` (verify this)
   - Or is it `effective = raw - own_declarations_given_to_opponent`?
   - Empirically derive the exact formula from `p1/p2` → `e1/e2`

3. **Produce a lookup table** for the scoring pipeline:
   - Input: raw_t1, raw_t2, declarations, game_mode, multiplier, khasara, baloot
   - Output: gp_t1, gp_t2
   - Must match 100% of archive results

4. **Special cases**:
   - Qayd penalty scoring (when `cc > 0`)
   - Qahwa flat 152 GP
   - Baloot transfer on Khasara
   - Double khasara (kaboot + khasara in same round)

### Output: `gbaloot/data/training/scoring_verification.json`

### Script: `scripts/reverse_engineering/verify_scoring.py`

---

## Execution Order

```
Mission 1 (State Machine)     ← No dependencies, do first
    ↓
Mission 2 (Move Labels)       ← Needs event understanding from M1
    ↓
Mission 3 (AI Benchmark)      ← Needs labeled moves from M2
    ↓
Mission 4 (Declarations)      ← Independent, can parallel with M2/M3
Mission 5 (Trick Resolution)  ← Independent, can parallel with M2/M3
Mission 6 (Scoring Extended)  ← Independent, can parallel with M2/M3
```

## How to Run

```bash
# Create output directories
mkdir -p scripts/reverse_engineering
mkdir -p gbaloot/data/training

# Run in order
python scripts/reverse_engineering/extract_state_machine.py
python scripts/reverse_engineering/label_player_types.py
python scripts/reverse_engineering/benchmark_kammelna_ai.py
python scripts/reverse_engineering/analyze_declarations.py
python scripts/reverse_engineering/verify_tricks.py
python scripts/reverse_engineering/verify_scoring.py
```

## Success Criteria

| Mission | Metric | Target |
|:---|:---|:---|
| 1. State Machine | All transitions documented | 100% coverage |
| 2. Move Labels | All e=10/e=11 windows identified | 100% |
| 3. AI Benchmark | Bot strategy fully documented | Qualitative |
| 4. Declarations | Declaration timing rules verified | 100% match |
| 5. Trick Resolution | Our resolver vs archive winner | 100% agreement |
| 6. Scoring | GP reproduction from raw data | 100% accuracy |
