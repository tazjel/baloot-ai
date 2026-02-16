# Task: Extract & Document the Bidding Phase Rules

## Objective

Reverse-engineer the **complete bidding phase rules** of Baloot by analyzing:
1. Real game data from 55 archived Kammelna games
2. The existing engine implementation
3. The KAMMELNA_SCHEMA.md reference document

Then add a comprehensive **"Bidding Phase (المزايدة)"** section to `gbaloot/data/KAMMELNA_SCHEMA.md`.

---

## Step 1: Read the Schema Reference

Read `gbaloot/data/KAMMELNA_SCHEMA.md` completely. Focus on:
- Section `e=2 — Bidding Action` (existing bid type definitions)
- Section `Al-Thalith (الثالث) — The Third Rule` (Qablik/beforeyou)
- Section `Doubling System (Al-Dabal)` (Ashkal interaction with bidding)

## Step 2: Analyze the Game Archives

The archives are at: `gbaloot/data/archive_captures/mobile_export/savedGames/`

Write a Python script (save as `scripts/tools/extract_bidding_patterns.py`) that:

```python
# Pseudocode — Claude should implement this fully
import json, glob, os
from collections import Counter, defaultdict

games_dir = "gbaloot/data/archive_captures/mobile_export/savedGames/"
files = glob.glob(os.path.join(games_dir, "*.json"))

# For each game file:
for f in files:
    data = json.load(open(f, encoding='utf-8'))
    for round_data in data.get('rs', []):
        events = round_data.get('ev', [])
        
        # Extract the BIDDING SEQUENCE for this round:
        # - Filter events where e == 2 (bidding actions)
        # - Record: player (p), bid type (b), game mode (gm), 
        #           trump suit (ts), round bidder (rb)
        # - Track the ORDER of bids (who bid first, second, etc.)
        
        bidding_events = [ev for ev in events if ev.get('e') == 2]
        
        # ANALYZE AND COLLECT:
        # 1. What bid sequences lead to Hokm? (pass/pass/hokom patterns)
        # 2. What bid sequences lead to Sun?
        # 3. When does "thany" (second round) appear?
        # 4. When does "wala" appear vs "waraq"?
        # 5. When does "beforeyou" (Qablik) appear?
        # 6. When does "ashkal" appear?
        # 7. What is the face-up card? (first card dealt, or round metadata)
        # 8. Which player seat bids first? (relation to dealer)
        # 9. How does trump suit selection work after a Hokm bid?

# OUTPUT: A structured report of all observed bidding patterns
```

### Key Questions to Answer from the Data

1. **Bidding Order**: Who bids first relative to the dealer? What is the clockwise order?
2. **Round 1 vs Round 2**: What triggers the transition from Round 1 to Round 2?
3. **Pass Mechanics**: How many passes end Round 1? How many passes in Round 2 cancel the hand?
4. **Hokm Flow**: `hokom` → trump suit selection → play starts. What events appear between?
5. **Sun Flow**: When can Sun be bid? Only in Round 2? Can it override Hokm?
6. **Ashkal**: When does `ashkal` appear in the sequence? Is it a separate bid or a modifier?
7. **Beforeyou (Qablik)**: In which games does it appear? What was the face-up card? Who declared it?
8. **Waraq (Cancel)**: Under what conditions does a round get cancelled? All 4 pass twice?
9. **Face-up Card**: Is the face-up card identifiable in the data? (Check round metadata or first card event)
10. **Dealer Rotation**: Does `dl` field in the round indicate the dealer? How does it rotate?

## Step 3: Read the Engine Implementation

Read these files to understand the current bidding implementation:

```
game_engine/logic/game.py          — handle_bid(), bidding flow
game_engine/logic/bidding_engine.py — if exists, the core bidding logic
game_engine/models/constants.py     — bid-related constants
```

Search for: `bid`, `bidding`, `auction`, `hokom`, `sun`, `ashkal`, `pass`, `round_1`, `round_2`

## Step 4: Write the Bidding Phase Section

Add a new section to `KAMMELNA_SCHEMA.md` BEFORE the "Al-Thalith" section (since Al-Thalith is a bidding sub-rule). Structure:

```markdown
## Bidding Phase (المزايدة)

### Overview
[High-level description of the two-round bidding system]

### Bidding Order
[Who starts, clockwise rotation, relation to dealer]

### Round 1 — First Bidding Round
[What can be bid: hokom or pass. Face-up card influence.]

### Round 2 — Second Bidding Round  
[What can be bid: hokom2, sun, ashkal, wala, waraq]
[When is Round 2 triggered?]

### Sun vs Hokm Priority
[Can Sun override Hokm? Under what conditions?]

### Trump Suit Selection
[After Hokm is claimed, how is the suit chosen?]

### Round Cancellation (Waraq)
[When all players pass both rounds]

### Ashkal (Doubled Stakes)
[When and how Ashkal is declared during bidding]

### Face-Up Card
[Its role in bidding decisions, influence on Al-Thalith]

### Bidding Sequence Examples
[3-4 real examples extracted from game archives, showing the full e=2 event sequence]
```

## Step 5: Cross-Reference and Verify

After writing the section:
1. Verify every rule against at least 2 game archive examples
2. Check the engine implementation matches the documented rules
3. Flag any discrepancies with ⚠️ annotations
4. Add engine status: ✅ implemented, ⚠️ partial, ❌ missing

## Deliverables

1. `scripts/tools/extract_bidding_patterns.py` — analysis script
2. Updated `gbaloot/data/KAMMELNA_SCHEMA.md` — new Bidding Phase section
3. Console output showing the analysis results and key patterns found
