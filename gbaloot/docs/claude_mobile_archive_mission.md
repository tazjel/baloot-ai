# Mission: Mobile Archive Parser & Benchmark Integration

> **Priority**: HIGH — We have 109 real game sessions ready for engine validation.  
> **Goal**: Parse source platform's mobile JSON archives → feed into GBaloot benchmark pipeline → achieve 100% trick resolution agreement.

---

## 1. Context & What We Have

We pulled **109 saved game JSON files** from the source platform mobile app via ADB.

**Location**: `gbaloot/data/archive_captures/mobile_export/savedGames/*.json`  
**Bonus data**: `gbaloot/data/archive_captures/mobile_export/highlights/` (9 stat files: bidStrength, catchings, cheatings, kaboot, lostBid, picWithAce, projectsScores, tensHunt, wonBid)

Each JSON file is a **complete game replay** — every bid, every card played, every trick winner, every round result. This is the richest dataset we've ever had.

---

## 2. Mobile Archive JSON Format (Fully Decoded)

Each file is a single JSON object. Here's the complete schema:

### Top-Level Fields

| Field | Type | Meaning |
|-------|------|---------|
| `v` | int | Format version (always 1) |
| `n` | string | Session name (Arabic, e.g. "جلسة 10") |
| `ps` | int[4] | Player user IDs (seats 1-4) |
| `psN` | string[4] | Player display names |
| `psRP` | int[4] | Player ranking points |
| `psRN` | int[4] | Player ranking level |
| `psCb` | int[4] | Player cosmetic badge |
| `psV` | int[4] | Player VIP status |
| `psSb` | int[4] | Player subscription status |
| `rL` | int | Number of rounds in this game |
| `Id` | int | Game/session ID |
| `t` | int | Game type/table |
| `chA` | int | Chat availability (1=enabled) |
| `gT` | int | Game table type |
| `pT` | int | Timestamp (epoch ms) |
| `s1` | int | **Final score team 1** (players 1,3) |
| `s2` | int | **Final score team 2** (players 2,4) |
| `rs` | array | **Array of rounds** — THE CORE DATA |

### Round Structure (`rs[i]`)

Each round is an object with a single key `r` containing an array of events:

```json
{ "r": [ event1, event2, ... ] }
```

### Event Types (the `e` field)

This is the critical encoding. Each event in the round's `r` array has an `e` field:

| `e` value | Event Type | Description |
|-----------|-----------|-------------|
| `15` | **Hand Dealt** | Contains `bhr` and `fhr` arrays (card bitmasks for before/after dealing) |
| `1` | **New Round Start** | `fc` = first card index, `t1s`/`t2s` = team cumulative scores |
| `2` | **Bid** | `p` = player, `b` = bid action, `gm` = game mode, `ts` = trump suit |
| `3` | **Declaration (Project)** | `p` = player, `prj` = declaration type, `prjC` = card bitmask |
| `4` | **Card Played** | `p` = player (1-4), `c` = card index (0-51) |
| `5` | **Kaboot** | Kaboot fold event |
| `6` | **Trick Won** | The player `p` from the PREVIOUS card play is the winner |
| `8` | **Chat Message** | `uid` = user ID, `msg` = message text |
| `12` | **Round Result** | `rs` object with full scoring breakdown |

### Event Detail: Bidding (e=2)

```json
{"p": 1, "e": 2, "b": "pass", "ts": 4, "rb": -1}
{"p": 4, "e": 2, "b": "hokom", "gm": 2, "ts": 4, "rb": 4}
{"p": 1, "e": 2, "b": "sun", "gm": 1, "ts": 4, "rb": 1}
{"p": 3, "e": 2, "b": "hokom2", "gm": 2, "ts": 4, "rb": 3}
{"p": 3, "e": 2, "b": "clubs", "gm": 2, "ts": 2, "rb": 3}
{"p": 4, "e": 2, "b": "triple", "gm": 2, "gem": 2, "rd": 4, "ts": 3, "rb": 4}
{"p": 1, "e": 2, "b": "hokomclose", "gm": 2, "gem": 1, "rd": 1, "ts": 3, "rb": 4, "hc": 1}
```

| Bid Field | Meaning |
|-----------|---------|
| `p` | Player seat (1-4, **1-indexed**) |
| `b` | Bid action: `pass`, `hokom`, `sun`, `hokom2`, `thany`, `wala`, `triple`, `hokomclose`, `clubs`, `diamonds`, `hearts`, `spades` |
| `gm` | Game mode chosen: 1 = SUN, 2 = HOKUM |
| `ts` | Trump suit: 1=♠, 2=♣, 3=♦, 4=♥ (only relevant for HOKUM) |
| `rb` | Round bidder (who set the current contract, -1 = nobody yet) |
| `gem` | Escalation multiplier |
| `rd` | Re-double player |
| `hc` | Hokom close flag |

### Event Detail: Card Played (e=4)

```json
{"p": 1, "e": 4, "c": 25}
{"p": 2, "e": 4, "c": 47}
```

- `p` = player seat (1-4, **1-indexed** — subtract 1 for 0-indexed seats)
- `c` = card index (0-51)

### Card Index Formula (ALREADY PROVEN in our codebase)

```
index = suit_index * 13 + rank_index

Suits:  0=♠, 1=♥, 2=♣, 3=♦
Ranks:  0=2, 1=3, ..., 5=7, 6=8, 7=9, 8=10, 9=J, 10=Q, 11=K, 12=A

Baloot only uses ranks 5-12 (7 through A).
Valid indices: 5-12, 18-25, 31-38, 44-51
```

**Use `gbaloot/core/card_mapping.py :: index_to_card(idx)`** — it's already written and verified.

### Event Detail: Trick Won (e=6)

The trick winner is indicated by `e=6`. The **player who won the trick** is identified by examining which player's `e=4` (card play) event has the **same `p` value** as the preceding set of 4 card plays, and who the `e=6` event appears after.

**CRITICAL**: Look at the sequence pattern:
```json
{"p": 1, "e": 4, "c": 25},   // Player 1 plays
{"p": 2, "e": 4, "c": 47},   // Player 2 plays
{"p": 3, "e": 4, "c": 19},   // Player 3 plays
{"p": 4, "e": 4, "c": 24},   // Player 4 plays
{"p": 2, "e": 6}             // Player 2 WINS the trick
```

The `p` field on the `e=6` event **is the winner** of that trick. And also the **leader of the next trick**.

### Event Detail: Declaration/Project (e=3)

```json
{"p": 1, "e": 3, "prj": 1}           // Player declares project type 1
{"p": 4, "e": 3, "prjC": 3584}       // Project cards (bitmask)
```

| `prj` value | Declaration Type |
|-------------|-----------------|
| 1 | Sira (sequence) |
| 5 | 50 (three of a kind) |
| 6 | 100 (four of a kind) |

### Event Detail: Round Result (e=12)

```json
{
  "e": 12,
  "rs": {
    "p1": 47,        // Team 1 round points
    "p2": 135,       // Team 2 round points
    "lmw": 2,        // Last match winner (team)
    "m": 2,          // Mode: 1=SUN, 2=HOKUM
    "em": 3,         // Escalation multiplier (if doubled/tripled)
    "r1": [],        // Team 1 declarations: [{"n":"sira","val":"20"}, {"n":"baloot","val":"20"}]
    "r2": [{"n":"sira","val":"20"}],  // Team 2 declarations
    "e1": 47,         // Team 1 card points earned
    "e2": 105,        // Team 2 card points earned
    "w": 2,           // Winner of this round (team 1 or 2)
    "s1": 5,          // Team 1 cumulative game score after this round
    "s2": 13,         // Team 2 cumulative game score after this round
    "b": 2,           // Bidder team
    "kbt": 1,         // Kaboot flag (if present = kaboot happened)
    "lr": 1           // Last round flag
  }
}
```

### Trump Suit Mapping (Bidding `ts` field)

**IMPORTANT** — The `ts` values in bidding are DIFFERENT from card_mapping suit indices:

| `ts` value | Suit |
|------------|------|
| 1 | ♠ Spades |
| 2 | ♣ Clubs |
| 3 | ♦ Diamonds |
| 4 | ♥ Hearts |

vs. card_mapping.py uses: 0=♠, 1=♥, 2=♣, 3=♦

**You must map between these carefully.**

---

## 3. What To Build

### Phase 1: Archive Parser (`gbaloot/tools/archive_parser.py`)

Create a new module that:

1. **Loads** a mobile archive JSON file
2. **Parses** the event stream into our existing data structures
3. **Outputs** a `ProcessedSession`-compatible format (or directly feeds the comparator)

```python
# Proposed interface
def parse_mobile_archive(archive_path: Path) -> list[dict]:
    """Parse a source platform mobile archive JSON into GBaloot-compatible events.
    
    Returns a list of event dicts matching the format expected by
    trick_extractor.extract_tricks() and comparator.compare_session().
    """
```

**The key challenge**: The existing `trick_extractor.py` expects events in our `ProcessedSession` format (with `action`, `fields.p.p` nesting, `played_cards` arrays, etc.). The mobile archives use a completely different format. You have TWO options:

#### Option A: Convert to ProcessedSession Format (RECOMMENDED)
Transform each mobile archive into the same event format that `trick_extractor.py` already understands. This reuses all existing comparison logic unchanged.

#### Option B: Write a New Extractor for Mobile Format
Write `archive_trick_extractor.py` that directly converts mobile JSON events into `ExtractedTrick` / `ExtractedRound` / `ExtractionResult` objects. These feed directly into `GameComparator._compare_trick()`.

**I RECOMMEND Option B** because:
- The mobile format is much simpler and richer than the SFS2X WebSocket stream
- We already have explicit trick winners (e=6), round results (e=12), game modes, trump suits
- No need to reconstruct state from partial WebSocket messages
- Cleaner, more maintainable code

### Phase 2: Archive Trick Extractor (`gbaloot/tools/archive_trick_extractor.py`)

If using Option B, build this extractor:

```python
def extract_tricks_from_archive(archive_path: Path) -> ExtractionResult:
    """Extract all tricks from a mobile archive file.
    
    Uses the existing ExtractionResult/ExtractedRound/ExtractedTrick 
    classes from gbaloot.core.trick_extractor.
    """
```

**Extraction logic** (walking the event array for each round):

```
For each round in game["rs"]:
    events = round["r"]
    
    1. Find e=2 events → determine game_mode and trump_suit
    2. Walk e=4 events → collect cards_by_seat (4 at a time)
    3. When e=6 appears → that's the trick winner, emit ExtractedTrick
    4. When e=12 appears → that's the round result, validate
    
    Build ExtractedRound with all tricks
```

**Key mappings needed:**
- Player `p` is 1-indexed in archives → convert to 0-indexed seats
- Trump suit `ts` mapping: 1→♠(0), 2→♣(2), 3→♦(3), 4→♥(1) for our suit indices
- Card index `c` uses same 0-51 encoding as our `card_mapping.py`
- `gm=1` → "SUN", `gm=2` → "HOKUM" (matches our `MODE_MAP`)

### Phase 3: Archive Benchmark Runner (`gbaloot/tools/run_archive_benchmark.py`)

A script that:

1. Scans `gbaloot/data/archive_captures/mobile_export/savedGames/`
2. Parses each game using the archive extractor
3. Feeds each `ExtractionResult` into `GameComparator`
4. Generates comparison reports and scorecard
5. Prints summary results

```python
"""Run GBaloot benchmark against mobile archive data."""

from pathlib import Path
from gbaloot.core.comparator import GameComparator, generate_scorecard
from gbaloot.tools.archive_trick_extractor import extract_tricks_from_archive

ARCHIVE_DIR = Path("gbaloot/data/archive_captures/mobile_export/savedGames")

def main():
    comparator = GameComparator()
    reports = []
    
    for archive_file in sorted(ARCHIVE_DIR.glob("*.json")):
        extraction = extract_tricks_from_archive(archive_file)
        # ... feed to comparator, collect reports
    
    scorecard = generate_scorecard(reports)
    # ... print results
```

### Phase 4: Bonus — Highlight Data Parser (Optional, Lower Priority)

The `highlights/` directory contains statistical summaries:
- `bidStrength` — Bidding strength analysis
- `catchings` — Catch play tracking
- `cheatings` — Cheat/qayd events
- `kaboot` — Kaboot (fold) data
- `lostBid` — Lost bids analysis
- `picWithAce` — Ace pickup plays
- `projectsScores` — Declaration scoring
- `tensHunt` — 10-hunting strategy data
- `wonBid` — Won bids analysis

These can be parsed later for strategy insights. Focus on the game replays first.

---

## 4. Existing Pipeline Files You Must Study

| File | Purpose | Your Interaction |
|------|---------|-----------------|
| `gbaloot/core/card_mapping.py` | Card index ↔ Card object conversion | **REUSE** `index_to_card()`, `suit_idx_to_symbol()`, `map_game_mode()` |
| `gbaloot/core/trick_extractor.py` | Defines `ExtractedTrick`, `ExtractedRound`, `ExtractionResult` | **REUSE** these dataclasses as your output format |
| `gbaloot/core/comparator.py` | `GameComparator` with `_compare_trick()` | **FEED** your extracted tricks into this |
| `gbaloot/core/models.py` | `ProcessedSession`, `GameEvent` | Reference only (your mobile data bypasses this) |
| `gbaloot/run_benchmark.py` | Current benchmark runner | **MODEL** your archive benchmark runner on this |
| `game_engine/models/card.py` | `Card(suit, rank)` class | Used by card_mapping |
| `game_engine/models/constants.py` | `ORDER_SUN`, `ORDER_HOKUM`, point values | Used by comparator |

---

## 5. Sample Data

Here is one complete round from `جلسة 10_1769181412467.json` for testing:

```json
{
  "r": [
    {"e": 15, "bhr": [633318732464128,141151952699424,1125972923383936,316659348803072], "fhr": [633335920726016,2392960356319328,1125972928102784,334285911363072]},
    {"p": 4, "e": 1, "fc": 44},
    {"p": 1, "e": 2, "b": "pass", "ts": 4, "rb": -1},
    {"p": 2, "e": 2, "b": "pass", "ts": 4, "rb": -1},
    {"p": 3, "e": 2, "b": "pass", "ts": 4, "rb": -1},
    {"p": 4, "e": 2, "b": "hokom", "gm": 2, "ts": 4, "rb": 4},
    {"p": 3, "e": 2, "b": "pass", "gm": 2, "ts": 4, "rb": 4},
    {"p": 1, "e": 2, "b": "pass", "gm": 2, "ts": 4, "rb": 4},
    {"p": 2, "e": 2, "b": "pass", "gm": 2, "ts": 4, "rb": 4},
    {"p": 4, "e": 2, "b": "pass", "gm": 2, "ts": 3, "rb": 4},
    {"p": 1, "e": 4, "c": 25},
    {"p": 2, "e": 4, "c": 47},
    {"p": 3, "e": 4, "c": 19},
    {"p": 4, "e": 3, "prj": 1},
    {"p": 4, "e": 4, "c": 24},
    {"p": 2, "e": 6},
    {"p": 2, "e": 4, "c": 51},
    {"p": 3, "e": 4, "c": 50},
    {"p": 4, "e": 3, "prjC": 3584},
    {"p": 4, "e": 4, "c": 48},
    {"p": 1, "e": 4, "c": 49},
    {"p": 2, "e": 6},
    {"p": 4, "e": 4, "c": 44},
    {"p": 1, "e": 4, "c": 46},
    {"p": 2, "e": 4, "c": 6},
    {"p": 3, "e": 4, "c": 21},
    {"p": 1, "e": 6},
    {"p": 1, "e": 4, "c": 12},
    {"p": 2, "e": 4, "c": 5},
    {"p": 3, "e": 4, "c": 8},
    {"p": 4, "e": 4, "c": 9},
    {"p": 1, "e": 6},
    {"p": 1, "e": 4, "c": 20},
    {"p": 2, "e": 4, "c": 31},
    {"p": 3, "e": 4, "c": 22},
    {"p": 4, "e": 4, "c": 45},
    {"p": 2, "e": 6},
    {"p": 4, "e": 3, "prj": 5},
    {"p": 4, "e": 4, "c": 11},
    {"p": 1, "e": 4, "c": 18},
    {"p": 2, "e": 4, "c": 33},
    {"p": 3, "e": 4, "c": 7},
    {"p": 4, "e": 6},
    {"p": 4, "e": 3, "prj": 5},
    {"p": 4, "e": 4, "c": 10},
    {"p": 1, "e": 4, "c": 23},
    {"p": 2, "e": 4, "c": 37},
    {"p": 3, "e": 4, "c": 32},
    {"p": 2, "e": 6},
    {"p": 4, "e": 4, "c": 35},
    {"p": 1, "e": 4, "c": 34},
    {"p": 2, "e": 4, "c": 38},
    {"p": 3, "e": 4, "c": 36},
    {"p": 2, "e": 6},
    {"e": 12, "rs": {"p1": 47, "p2": 135, "lmw": 2, "m": 2, "r1": [], "r2": [{"n": "sira", "val": "20"}], "e1": 47, "e2": 105, "w": 2, "s1": 5, "s2": 13, "b": 2}}
  ]
}
```

### Walking Through This Round

1. **e=15**: Cards dealt (bitmask format, decode if needed)
2. **e=1**: Round start, first card is index 44 (♦Q)
3. **e=2 sequence**: Bidding — all pass, then P4 bids hokom, trump ♥ (ts=4)
4. **Card plays (e=4) + trick wins (e=6)**:
   - **Trick 1**: P1→c25(♣A), P2→c47(♦9), P3→c19(♥A), P4→c24(♣K) → P2 wins
   - **Trick 2**: P2→c51(♦A), P3→c50(♦K), P4→c48(♦10), P1→c49(♦J) → P2 wins
   - And so on for 8 tricks total
5. **e=12**: Round result — Team 2 wins with 135 pts, Team 2 had a sira declaration

### Card Examples from This Round

| Index | Suit*13+Rank | Card |
|-------|-------------|------|
| 25 | 1*13+12 | ♥A (Ace of Hearts) → but wait: suit 1=♥, rank 12=A ✓ |
| 47 | 3*13+8 | ♦10 |
| 19 | 1*13+6 | ♥8 |
| 24 | 1*13+11 | ♥K |
| 51 | 3*13+12 | ♦A |
| 44 | 3*13+5 | ♦7 |

Wait — let me recalculate card 25:
- 25 / 13 = 1 remainder 12 → Suit 1 (♥), Rank 12 (A) = **A♥**

Card 47: 47/13 = 3 remainder 8 → Suit 3 (♦), Rank 8 (10) = **10♦**

Card 19: 19/13 = 1 remainder 6 → Suit 1 (♥), Rank 6 (8) = **8♥**

This all checks out with our existing `card_mapping.py`.

---

## 6. Edge Cases & Gotchas

1. **Player indexing**: Archives use 1-4 (1-indexed). Our engine uses 0-3 (0-indexed). **Always subtract 1.**
2. **Trump suit encoding differs**: `ts` in bidding = {1:♠, 2:♣, 3:♦, 4:♥}. Our `suit_idx` = {0:♠, 1:♥, 2:♣, 3:♦}. Build a mapping.
3. **Declaration events (e=3) may interleave with card plays (e=4)** — don't let them confuse your card collection for a trick.
4. **e=5 (kaboot)**: The round may end early if a team folds. Handle incomplete tricks (fewer than 8 tricks in a round).
5. **Some games have chat messages (e=8)** interleaved — skip these.
6. **The `e=6` (trick won)** appears BETWEEN tricks. The `p` on the e=6 event is the winner AND the leader of the next trick.
7. **Escalation bids**: `triple`, `hokomclose` — the `gem` field tracks the multiplier. Not relevant for trick resolution but important for scoring validation.
8. **Round result `e1`/`e2`** are card points earned, while `p1`/`p2` include declarations. Use both for validation.
9. **The `bhr` and `fhr` arrays** in e=15 are bitmasks for cards before/after the deal. They could be decoded for full hand reconstruction, but this is optional — card plays already give us everything.

---

## 7. Validation Targets

After building the parser, validate against these known facts from the sample game (جلسة 10):

- **8 rounds played** (`rL: 5` in this game — wait, this says 5 but we see more rounds. `rL` might be something else. Count the `rs` array length instead.)
- **Final score**: Team 1 = 49, Team 2 = 184
- **Each round has exactly 8 tricks** (except kaboot rounds which may have fewer)
- **Trick winners should match engine computation** using our `_compute_winner_locally()` from comparator.py
- **Card point totals per round** should be 26 (SUN) or 16+36=52 (HOKUM with trump cards) — actually it's more nuanced, validate with engine

---

## 8. File Structure to Create

```
gbaloot/
├── tools/
│   ├── archive_parser.py          # Core parsing logic
│   ├── archive_trick_extractor.py # Mobile → ExtractedTrick converter
│   └── run_archive_benchmark.py   # Benchmark runner script
├── tests/
│   ├── test_archive_parser.py     # Parser unit tests
│   └── test_archive_extractor.py  # Extractor tests
└── data/
    └── archive_captures/
        └── mobile_export/
            ├── savedGames/        # 109 JSON files (already here)
            └── highlights/        # 9 stat files (already here)
```

---

## 9. Success Criteria

1. **Parser correctly reads all 109 archive files** without errors
2. **Extractor produces valid `ExtractionResult`** objects with correct trick counts
3. **GameComparator achieves high trick resolution agreement** (target: >95%)
4. **Scorecard generation works** with archive data
5. **Edge cases handled**: kaboot (early end), triple/double bids, interleaved declarations
6. **Unit tests** covering parser, extractor, and integration

---

## 10. Quick Start Command

After building, test with:

```bash
python -m gbaloot.tools.run_archive_benchmark
```

Expected output:
```
GBaloot Archive Benchmark
═══════════════════════════════════
Sessions analyzed: 109
Total tricks: ~XXXX
Trick resolution: XX.X% (badge: green/yellow/red)
Point calculation: XX.X%
SUN mode: XX.X%
HOKUM mode: XX.X%
```

---

## Appendix: Team Structure

In the mobile archives:
- **Team 1** = Players 1, 3 (seats 0, 2 in 0-indexed)
- **Team 2** = Players 2, 4 (seats 1, 3 in 0-indexed)

This matches our engine's team structure.
