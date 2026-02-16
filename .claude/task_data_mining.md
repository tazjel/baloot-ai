# Milestone: Empirical Data Mining from Professional Baloot Games

> **Model**: Claude Opus
> **Priority**: 🔴 HIGH — Must complete before Game Theory Enhancements (Phase 2+)
> **Principle**: Every game theory parameter must be grounded in empirical evidence from real professional play. No theoretical guesses.

## What You Have

### Data Source
- **109 professional games** played against top-ranked Baloot players on Kammelna
- Location: `gbaloot/data/archive_captures/mobile_export/savedGames/*.json`
- Schema: `gbaloot/data/KAMMELNA_SCHEMA.md` (1,172 lines — READ THIS FIRST)
- New games are added daily via `/sync` workflow

### Already Completed (Engine Reverse-Engineering Milestone)
These 6 outputs exist in `gbaloot/data/training/` — **USE THEM, don't redo them**:

| File | What It Contains |
|:---|:---|
| `event_state_machine.json` | Complete FSM of all 60 event transitions across 109 games |
| `move_labels.json` | 47,430 moves labeled as HUMAN or BOT (82 bot moves found) |
| `kammelna_ai_benchmark.json` | Kammelna bot plays 86% passive bids, 25% trick win rate |
| `declaration_analysis.json` | 1,769 declarations with timing and validation data |
| `trick_resolution_verify.json` | 8,107 tricks verified at 100% agreement |
| `scoring_verification.json` | 1,095 rounds, 100% GP match |

### Critical Schema Corrections (discovered during reverse-engineering)
- **`e=6.p` is NOT the trick winner** — it's an animation target. Compute winners from card logic
- **`result.m` = game MODE** (1=SUN, 2=HOKUM), NOT multiplier
- **Suit mapping**: Clubs=offset 31, Diamonds=offset 44 (schema originally had them swapped)
- **`prj=5` (khamsin)** is UI-only, never scored
- **SUN radda** uses `"double"`/`"redouble"` strings, not `"beforeyou"`
- **Missing `s1`/`s2` in result** = loser gets 0 GP (verified 405/405 cases)

---

## Mission 1: Professional Bidding Database

**Goal**: Build the definitive dataset of what professional players bid given their hand, to calibrate EV bidding thresholds.

### What to Extract

For every non-pass bid (`e=2` where `b` ≠ `"pass"`, `"wala"`, `"thany"`, `"waraq"`), extract:

```python
{
    # Identity
    "game_id": str,             # Session name
    "round_idx": int,           # Round number within the game
    "player_seat": int,         # 1-4

    # Hand at bid time
    "hand_cards": [int],        # 8 card IDs (decode from e=15 bhr bitmask)
    "floor_card": int,          # fc from e=1 (the face-up card)
    
    # Bid context
    "bid": str,                 # "hokom", "sun", "ashkal", "hokom2", suit names
    "bidding_round": 1 | 2,     # R1 or R2
    "seat_position": int,       # Position relative to dealer (1=first, 4=dealer)
    "previous_bids": [str],     # All bids before this one in this round
    "game_mode_chosen": str,    # Final mode: "SUN" or "HOKUM"
    "trump_suit": str | None,   # For Hokum only
    
    # Match context
    "team_score": int,          # Bidder's team score at round start (from t1s/t2s)
    "opponent_score": int,      # Opponent team score
    
    # Hand metrics (COMPUTE THESE)
    "trump_count": int,         # Cards matching floor_card suit (for R1 Hokum)
    "aces": int,                # Number of aces in hand
    "kings": int,
    "queens": int,
    "jacks": int,
    "high_cards": int,          # A+K+Q+J total
    "point_value": int,         # Total card points in hand (using Hokum or Sun values)
    "voids": int,               # Suits with 0 cards
    "singletons": int,          # Suits with exactly 1 card
    "longest_suit": int,        # Length of longest suit
    
    # Outcome (ground truth)
    "round_won": bool,          # Did bidding team win this round?
    "gp_earned": int,           # Game points earned (from e=12 result)
    "khasara": bool,            # Was it a sweep?
    "was_doubled": bool,        # Was there any doubling?
    "multiplier": int,          # Final multiplier (1, 2, 4, etc.)
}
```

### Also Extract: All PASSES
For every `b="pass"` or `b="wala"`, extract the same hand metrics. This is equally important — we need to know what hands pros **don't** bid with.

### Analysis to Produce
After extraction, compute and save:

1. **Bidding threshold matrix**: For every (trump_count, high_cards) pair, what % of the time do pros bid Hokum?
   ```
   trump=3, high=2 → 45% bid Hokum
   trump=4, high=2 → 78% bid Hokum
   trump=5, high=1 → 91% bid Hokum
   ```

2. **Sun bidding profile**: What hand metrics predict a Sun bid? (aces count, point total, void count)

3. **Win rate by hand strength**: For hands that were bid, group by (trump_count, high_cards) and compute win rate
   ```
   trump=3, high=2 → bid 45%, when bid won 52%
   trump=4, high=3 → bid 92%, when bid won 78%
   ```

4. **Position effect**: Does seat position (1st vs 4th to bid) change bidding aggressiveness?

5. **Score-dependent bidding**: At what scores do pros take riskier bids? Compare bids at 0-0 vs behind vs ahead.

### Output
```
gbaloot/data/training/pro_bidding_database.json     # Raw decision records
gbaloot/data/training/bidding_thresholds.json        # Threshold matrix
gbaloot/data/training/bidding_analysis_report.md     # Human-readable analysis
```

### Script: `scripts/data_mining/mine_bidding_data.py`

---

## Mission 2: Professional Card Play Database

**Goal**: Build a dataset of every card play decision with complete game context, to train trick play AI.

### Critical Prerequisite
Read `move_labels.json` — exclude all BOT moves (where `player_type = "BOT"`). We only want HUMAN professional decisions.

### What to Extract

For every card play (`e=4`), extract:

```python
{
    # Identity
    "game_id": str,
    "round_idx": int,
    "trick_number": int,        # 1-8 (or 1-5 depending on format)
    "position_in_trick": int,   # 1=leader, 2=second, 3=third, 4=last
    
    # Decision
    "card_played": int,         # Card ID played
    "hand_before": [int],       # Player's hand BEFORE this play (reconstruct by tracking)
    "legal_moves": [int],       # All cards they could legally play (reconstruct from rules)
    "num_options": int,         # len(legal_moves)
    
    # Trick context
    "cards_on_table": [int],    # Cards already played this trick (0-3 cards)
    "lead_suit": str | None,    # Suit of the first card (if not leader)
    "current_winner": int | None, # Seat currently winning the trick
    
    # Game context
    "game_mode": str,           # "SUN" or "HOKUM"
    "trump_suit": str | None,   # For Hokum
    "tricks_won_my_team": int,  # My team's tricks so far
    "tricks_won_opponent": int, # Opponent tricks so far
    "points_my_team": int,      # Estimated points so far
    "points_opponent": int,
    
    # Card tracking context
    "cards_played_so_far": [int],  # All cards played in previous tricks
    "cards_remaining": int,        # Total cards left unplayed
    "trump_played_count": int,     # How many trumps have been played
    
    # What the player knows
    "partner_seat": int,        # Who is their partner?
    "is_bidding_team": bool,    # Is this player on the bidding team?
    
    # Outcome
    "won_trick": bool,          # Did this player's team win this trick?
    "trick_points": int,        # Points in this trick
    "round_won": bool,          # Did their team win the round?
    
    # Labels
    "is_human": bool,           # From move_labels.json — True if HUMAN
}
```

### Reconstruction Requirements
- You must **track each player's hand** card-by-card as tricks are played (start from `bhr` bitmask, subtract played cards)
- You must **compute legal moves** based on Baloot rules: must follow lead suit if possible, can trump if void in lead suit
- You must **compute current trick winner** based on card hierarchy (use the verified trick resolution logic)

### Analysis to Produce

1. **Lead card frequency table**: When leading, what do pros lead with?
   - By suit (trump first? ace first? low card?)
   - By trick number (opening lead vs mid-game vs endgame)
   - By position (bidder leading vs defender leading)

2. **Follow play patterns**: When following suit, do pros play high or low?
   - Partner currently winning → play low (don't waste points)
   - Opponent winning → play high (try to take)
   - Quantify these tendencies from the data

3. **Trump usage**: When do pros trump?
   - Immediately when void in lead suit?
   - Hold trump for later tricks?
   - Trump frequency by trick number

4. **Discard patterns**: When void in lead suit and choosing not to trump, what do pros discard?
   - Do they shed point cards? Specific suits?
   - Signal to partner through discards?

5. **Endgame play** (last 2-3 tricks): Extract complete endgame positions
   - All 4 hands known, few cards left → these are solvable positions
   - Did the pro play optimally? (Check via exhaustive search)

### Output
```
gbaloot/data/training/pro_card_play_database.json    # Raw decision records (HUMAN only)
gbaloot/data/training/lead_frequency_table.json      # Lead preferences
gbaloot/data/training/play_patterns_report.md        # Human-readable analysis
gbaloot/data/training/endgame_positions.json          # Solvable endgame states
```

### Script: `scripts/data_mining/mine_card_play_data.py`

---

## Mission 3: Doubling & Risk Management Database

**Goal**: Build the dataset of when pros double/redouble, at what scores, and outcomes — to calibrate Kelly Criterion thresholds.

### What to Extract

For every doubling-related bid (`b` in `["double", "redouble", "hokomclose", "beforeyou", "radda", "gahwa"]`), extract:

```python
{
    # Identity
    "game_id": str,
    "round_idx": int,
    
    # Decision
    "action": str,              # The doubling bid made
    "doubling_level": int,      # Level AFTER this action (gem value: 1=double, 2=triple, 3=redouble, 4=qahwa)
    "player_seat": int,
    "is_bidding_team": bool,    # Is doubler on the team that bid the game?
    
    # Hand strength
    "hand_cards": [int],        # Doubler's hand
    "hand_metrics": {...},      # Same metrics as Mission 1 (aces, high_cards, etc.)
    
    # Game context
    "game_mode": str,           # "SUN" or "HOKUM"
    "trump_suit": str | None,
    
    # Score context (CRITICAL for Kelly)
    "team_score_before": int,   # Doubler's team score at round start
    "opponent_score_before": int,
    "score_differential": int,  # team - opponent (positive = ahead, negative = behind)
    "points_to_win": int,       # 152 - team_score = how many more needed
    
    # Outcome
    "round_won": bool,          # Did doubler's team win?
    "gp_earned": int,           # GP result
    "gp_lost": int,             # GP lost (if lost)
    "khasara": bool,
}
```

### Also Extract: Doubling Opportunities NOT Taken
When a player COULD have doubled but chose not to (passed during doubling phase), record:
- Their hand strength
- The score context
- This is essential — we need to know the boundary between "double" and "don't double"

### Analysis to Produce

1. **Doubling win rate by level**:
   ```
   Double: pros win X% of doubled rounds
   Triple: pros win Y%
   Qahwa: pros win Z%
   ```

2. **Doubling by score differential**: Plot doubling frequency vs (team_score - opponent_score)
   - Do pros double more when behind? (Desperate doubles)
   - Do pros double more when ahead? (Closing doubles)
   - Find the sweet spot

3. **Hand strength vs doubling**: Minimum hand metrics needed before pros double
   - What's the weakest hand anyone doubled with?
   - What's the threshold where >50% of pros double?

4. **Kelly Criterion validation**: Compute optimal Kelly fraction f* = (pb - q)/b for each observed doubling decision
   - How close are real pros to Kelly-optimal?

### Output
```
gbaloot/data/training/pro_doubling_database.json     # Raw decision records
gbaloot/data/training/doubling_thresholds.json       # Score-dependent thresholds
gbaloot/data/training/kelly_analysis_report.md       # Kelly Criterion validation
```

### Script: `scripts/data_mining/mine_doubling_data.py`

---

## Mission 4: Partnership Signaling Extraction

**Goal**: Discover if professional players use systematic signaling through their card play — leads, discards, count signals.

### What to Extract

#### 4A: Lead Signals
For every trick-leading card play, extract:
```python
{
    "lead_card": int,
    "lead_card_rank": str,      # "A", "K", "Q", "J", "10", "9", "8", "7"
    "lead_card_suit": str,
    "leader_hand": [int],       # Leader's full hand at this point
    "leader_suit_length": int,  # How many of the led suit does leader have?
    "leader_has_ace": bool,     # Does leader have ace of this suit?
    "partner_response": int,    # What card did partner play?
    "partner_had_suit": bool,   # Did partner have the led suit?
    "trick_won_by_team": bool,  # Did the leading team win?
}
```

#### 4B: Discard Signals
When a player cannot follow suit, what do they discard?
```python
{
    "player_seat": int,
    "discarded_card": int,
    "discarded_suit": str,
    "discarded_rank": str,
    "player_hand": [int],       # Hand at this point
    "suits_in_hand": {str: int}, # Count of each suit remaining
    "led_suit": str,            # The suit they couldn't follow
    "game_mode": str,
    "trick_number": int,
    # Did they discard from their weakest suit? Strongest? 
    "discarded_from_shortest_suit": bool,
    "discarded_highest_in_suit": bool,
}
```

### Analysis to Produce

1. **Lead conventions**: 
   - Do pros lead ace from A-K (classic high-low)?
   - Do pros lead low from length (4th best)?
   - Quantify: "When pros lead an Ace, they have A+K X% of the time"

2. **Discard patterns**:
   - Do discards signal suit preference to partner?
   - High discard = strength in that suit? Or shedding losers?
   - Quantify correlations between discard rank and remaining hand

3. **Count signals**:
   - Do pros play high-low to show even count? Low-high for odd?
   - Test correlation: second card played in suit vs total length

4. **Signal reliability**: For each potential signal, compute P(signal_interpretation_correct)
   - If reliability < 60%, the signal isn't real — don't implement it

### Output
```
gbaloot/data/training/lead_signals.json
gbaloot/data/training/discard_signals.json  
gbaloot/data/training/signaling_analysis_report.md
```

### Script: `scripts/data_mining/mine_signals.py`

---

## Mission 5: Round Outcome Predictors

**Goal**: Build a dataset that connects hand distributions, bidding, and strategic choices to round outcomes — the foundation for win probability estimation.

### What to Extract

For every round, extract a comprehensive round summary:

```python
{
    # Identity
    "game_id": str,
    "round_idx": int,
    
    # Initial conditions
    "team1_hands": [[int], [int]],   # Seats 1 & 3 hands
    "team2_hands": [[int], [int]],   # Seats 2 & 4 hands
    "floor_card": int,
    
    # Bidding outcome
    "game_mode": str,            # "SUN" or "HOKUM"
    "trump_suit": str | None,
    "bidding_team": 1 | 2,       # Which team won the bid
    "bidder_seat": int,          # Who bid
    "bid_type": str,             # Original bid
    "multiplier": int,           # 1, 2, 4, 8 (from doubling)
    
    # Match context
    "team1_score_before": int,
    "team2_score_before": int,
    
    # Computed hand metrics for BIDDING team
    "bidder_trump_count": int,
    "bidder_high_cards": int,
    "bidder_aces": int,
    "bidder_point_total": int,
    "partner_trump_count": int,  # Bidder's partner
    "partner_high_cards": int,
    "combined_trump": int,       # Team trump total
    "combined_aces": int,
    
    # Computed hand metrics for DEFENDING team
    "defender_trump_count": int,
    "defender_combined_aces": int,
    
    # Outcome
    "winner_team": 1 | 2,
    "team1_tricks": int,
    "team2_tricks": int,
    "team1_raw_points": int,
    "team2_raw_points": int,
    "team1_gp": int,
    "team2_gp": int,
    "khasara": bool,
    "declarations": [...],       # Any declarations made
}
```

### Analysis to Produce

1. **Win probability model**: 
   - P(bidding_team_wins | combined_trump, combined_high_cards, game_mode)
   - Build a lookup table or logistic regression from the data
   - This is THE core input for EV bidding

2. **Khasara predictors**: What combination of metrics leads to sweeps?
   - "When combined trump ≥ 6 AND combined aces ≥ 3 → khasara X% of the time"

3. **Mode comparison**: Sun vs Hokum win rates by hand strength
   - When is Sun better than Hokum for the same hand?

4. **Score influence**: Does the match score bias outcomes? (Psychological pressure at 140-140?)

### Output
```
gbaloot/data/training/round_outcomes.json            # All round summaries
gbaloot/data/training/win_probability_model.json     # P(win) lookup tables
gbaloot/data/training/outcome_analysis_report.md     # Insights
```

### Script: `scripts/data_mining/mine_round_outcomes.py`

---

## Execution Order

```
Mission 1 (Bidding)     ← Start here — most impactful for EV bidding
Mission 2 (Card Play)   ← Most complex extraction (hand tracking)  
Mission 3 (Doubling)    ← Quick extraction, high value for Kelly
Mission 4 (Signals)     ← Depends on M2 (same hand tracking logic)
Mission 5 (Outcomes)    ← Synthesis — uses all 4 hands, can run in parallel
```

Missions 1, 3, 5 are independent. Mission 4 reuses Mission 2's hand reconstruction.

## How to Run

```bash
# Create directories
mkdir -p scripts/data_mining
mkdir -p gbaloot/data/training

# Run all extractions
python scripts/data_mining/mine_bidding_data.py
python scripts/data_mining/mine_card_play_data.py
python scripts/data_mining/mine_doubling_data.py
python scripts/data_mining/mine_signals.py
python scripts/data_mining/mine_round_outcomes.py
```

## Important Instructions for Claude

1. **READ THE SCHEMA FIRST**: `gbaloot/data/KAMMELNA_SCHEMA.md` — all 1,172 lines. Do not guess key meanings.
2. **USE the reverse engineering outputs** in `gbaloot/data/training/` — don't re-extract what already exists.
3. **Apply the schema corrections** listed above (e=6.p is NOT winner, result.m is MODE, suit mapping fix).
4. **Filter BOT moves** using `move_labels.json` — only 82 moves are BOT, but exclude them from pro analysis.
5. **Test on 3 games first** before processing all 109 — verify schema parsing is correct.
6. **Every analysis claim must cite sample size** — "Based on N=1,629 rounds..." not "approximately..."
7. **Save all outputs as pretty-printed JSON** with `indent=2` for human readability.
8. **Generate markdown reports** alongside JSON — the reports should contain actionable thresholds, not just raw data.

## Success Criteria

| Mission | Metric | Target |
|:---|:---|:---|
| 1. Bidding | Records extracted | ~12,000+ bid events |
| 1. Bidding | Threshold matrix produced | (trump_count × high_cards) grid |
| 2. Card Play | Decisions with legal moves computed | ~14,000+ plays |
| 2. Card Play | Endgame positions extracted | ~5,000+ (last 3 tricks) |
| 3. Doubling | Decisions + opportunities captured | All doubling phases |
| 3. Doubling | Kelly validation produced | f* computation for each decision |
| 4. Signals | Lead/discard patterns with reliability scores | P > 0.6 = real signal |
| 5. Outcomes | Round summaries with full hand data | 1,629 rounds |
| 5. Outcomes | Win probability model produced | P(win) lookup table |
