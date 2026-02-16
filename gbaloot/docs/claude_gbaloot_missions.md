# GBaloot — Improvement Missions for Claude

> **What is this?** A structured mission brief for Claude MAX. Each mission is self-contained with context, goals, files to read, and acceptance criteria. Pick a mission, read the required files, and deliver.

---

## System Context

GBaloot is a **benchmark lab** that captures live Baloot games from professional platforms via WebSocket interception, decodes the SFS2X binary protocol, extracts game events (tricks, bids, scores), and compares them against our own game engine to validate correctness.

### Current Baseline (Feb 2026)
| Metric | Value |
|--------|-------|
| Overall trick agreement | 96.8% (95 tricks) |
| HOKUM agreement | 100% (41/41) |
| SUN agreement | 94.4% (51/54) |
| Point consistency | 100% (3/3 rounds) |
| Sessions with game data | 8 / 68 |
| True engine errors | 0 (3 divergences = data extraction bug) |

### Architecture
```
Capture (Playwright WS) → Decode (SFS2X binary) → Extract (tricks/bids)
       → Compare (dual-engine) → Scorecard → Report
```

### File Map

| Layer | Key Files |
|-------|-----------|
| **Capture** | `capture_session.py`, `core/capturer.py` |
| **Decode** | `core/decoder.py`, `core/event_types.py` |
| **Map** | `core/card_mapping.py` |
| **Extract** | `core/trick_extractor.py`, `core/bid_extractor.py` |
| **Compare** | `core/comparator.py`, `core/bid_comparator.py` |
| **Score** | `core/point_tracker.py`, `core/round_report.py` |
| **State** | `core/reconstructor.py`, `core/state_builder.py`, `core/models.py` |
| **Autopilot** | `core/gboard.py`, `autopilot.py` |
| **Report** | `core/report_exporter.py`, `sections/benchmark.py` |
| **Analytics** | `core/match_analytics.py`, `sections/analytics.py` |
| **Tests** | `tests/test_*.py` (16 test files) |

### Conventions
- Python 3.11+, `from __future__ import annotations` everywhere
- Pure functions preferred, dataclasses for data containers
- `logging.getLogger(__name__)` for debug output
- Type hints on all function signatures
- Tests use pytest, run with: `python -m pytest gbaloot/tests/ --tb=short -q`
- Never use the word "Kammelna" in code — use "Source" or "source platform"
- Source uses 1-indexed seats; our engine uses 0-indexed

---

## Mission 1: Fix the 0xA0 Decoder (Zlib Frames)

**Priority**: 🔴 HIGH — Blocks data completeness
**Effort**: Small (1 file, ~30 lines)

### Problem
The `SFS2XDecoder` in `core/decoder.py` currently cannot process `0xA0` frames (zlib-compressed SFS2X messages). These frames are silently skipped, meaning we lose ~20% of captured game data. This directly limits the number of tricks available for benchmarking.

### What to Do
1. **Read** `gbaloot/core/decoder.py` — understand the `decode_message()` flow
2. **Add** zlib decompression for frames starting with byte `0xA0`:
   - Strip the first byte (`0xA0`)
   - `zlib.decompress()` the remaining bytes
   - Feed the decompressed payload back into the existing `0x80` parsing logic
3. **Handle** edge cases: invalid zlib data, partial frames, empty payloads
4. **Write tests** in `gbaloot/tests/test_decoder.py` covering:
   - Valid 0xA0 frame → successful decode
   - Corrupted zlib data → graceful error
   - Mixed stream of 0x80 and 0xA0 frames

### Acceptance Criteria
- `decode_message()` successfully decodes 0xA0 frames
- Existing 0x80 tests still pass
- At least 3 new test cases for 0xA0 handling
- Run benchmark again after fix to see if agreement improves

---

## Mission 2: Divergence Root-Cause Analyzer

**Priority**: 🟡 MEDIUM — Improves debugging velocity
**Effort**: Medium (new module + integration)

### Problem
When the comparator finds a divergence (engine disagrees with source), the current output is a raw data dump. An engineer must manually trace through seat mappings, card indices, and trick resolution rules to determine: is this an engine bug, or a data extraction bug?

### What to Do
1. **Read** `gbaloot/core/comparator.py` — the `Divergence` dataclass and `_record_divergence()` method
2. **Read** `gbaloot/core/trick_extractor.py` — how tricks are extracted from events
3. **Create** `gbaloot/core/divergence_analyzer.py` with a function:
   ```python
   def analyze_divergence(div: Divergence) -> DivergenceAnalysis:
       """Deep-analyze a divergence to determine root cause."""
   ```
4. The analyzer should:
   - Re-resolve the trick using our engine, showing step-by-step card comparison
   - Check if the source winner seat could be a ±1 indexing error (common bug)
   - Check if lead suit was misidentified (wrong first card in sequence)
   - Check if cards were in wrong positions (seat mapping error)
   - Classify the root cause: `ENGINE_BUG`, `EXTRACTION_BUG`, `SEAT_MAPPING_ERROR`, `AMBIGUOUS`
   - Produce a human-readable explanation string
5. **Integrate** into `comparator.py` — auto-analyze each divergence when recorded
6. **Write tests** with synthetic divergences covering each root cause type

### Output Shape
```python
@dataclass
class DivergenceAnalysis:
    divergence_id: str
    root_cause: str          # ENGINE_BUG | EXTRACTION_BUG | SEAT_MAPPING_ERROR | AMBIGUOUS
    confidence: float        # 0.0 - 1.0
    explanation: str         # Human-readable paragraph
    engine_trace: list[str]  # Step-by-step trick resolution
    suggested_fix: str       # What to investigate or fix
```

---

## Mission 3: Declaration Comparison (Baloot, Sawa, Sira)

**Priority**: 🟡 MEDIUM — Expands benchmark coverage
**Effort**: Medium (extractor + comparator extensions)

### Problem
The current benchmark only compares **trick winners** and **point totals**. It does NOT verify that **declarations** (Baloot, Sawa, Sira, Khamsin, Mi'a) are extracted and validated correctly. Declarations affect scoring significantly — a missed Baloot declaration is worth 44 points in SUN.

### What to Do
1. **Read** `gbaloot/core/trick_extractor.py` — the `extract_tricks()` function
2. **Read** `gbaloot/core/decoder.py` — look for the `dp` (declarations per player) field in decoded events
3. **Read** `game_engine/logic/scoring_engine.py` — how declarations affect scoring
4. **Create or extend** `gbaloot/core/declaration_extractor.py`:
   ```python
   def extract_declarations(events: list[dict]) -> list[ExtractedDeclaration]:
       """Extract all declarations from session events."""
   ```
5. **Extend** `comparator.py` to compare declarations:
   - Source says Player 2 declared Baloot → our engine should also detect Baloot for that player
   - Compare declaration timing (which trick it was declared in)
   - Track declaration point impact
6. **Add** declaration agreement percentages to the scorecard
7. **Write tests** covering: Baloot detection, Sawa detection, no-declaration baseline

### Key SFS2X Fields
```python
# In game_state payloads:
"dp": [[], ["baloot"], [], []]  # declarations per seat (1-indexed)
# dp[i] is a list of declaration strings for seat i+1
```

---

## Mission 4: Scoring Deep-Dive Comparator

**Priority**: 🟡 MEDIUM — Full scoring verification
**Effort**: Medium-Large

### Problem
We verify that combined card points are consistent but don't break down the scoring pipeline:
1. Card points per trick × winner → Are individual trick scores correct?
2. Last-trick bonus (10 points) → Was it applied correctly?
3. Game Points rounding (SUN: 26 total, HOKUM: 16 total) → correct?
4. Kaboot/Galoss multipliers → detected and applied?
5. Declaration modifiers → added after GP rounding?

### What to Do
1. **Read** `gbaloot/core/point_tracker.py` — the full scoring analysis pipeline
2. **Read** `game_engine/logic/scoring_engine.py` — canonical scoring rules
3. **Extend** `point_tracker.py` to track per-trick point breakdowns:
   - Each trick: who won, what cards, how many points
   - Running totals per team
   - Flag if a trick's engine-calculated points differ from the running delta in the source
4. **Add** Kaboot/Galoss detection:
   - If one team won all 8 tricks → Kaboot (double points)
   - If one team won 0 tricks → Galoss (all points to opponent)
   - Compare with source's final game point assignment
5. **Add** comprehensive scoring verification to the scorecard:
   - `trick_point_accuracy`: % of tricks with matching point calculations
   - `round_score_accuracy`: % of rounds with matching final GP
   - `special_condition_accuracy`: Kaboot/Galoss detection accuracy
6. **Write tests** for edge cases: Kaboot round, Galoss round, Sun vs Hokum scoring differences

---

## Mission 5: Live Session Progress Dashboard

**Priority**: 🟢 NICE-TO-HAVE — Developer experience
**Effort**: Large (new module + terminal UI)

### Problem
When a capture session is running, there's no real-time visibility into what's being captured. The user plays games while the capture runs silently. A live progress view would show tricks being captured, decoded, and compared in real-time.

### What to Do
1. **Read** `gbaloot/capture_session.py` — the main capture loop
2. **Read** `gbaloot/core/capturer.py` — how WS messages are intercepted
3. **Create** `gbaloot/core/live_monitor.py`:
   - Subscribe to the capture event stream
   - Decode events in real-time (using existing decoder)
   - Track: tricks captured, current round/trick, bidding phase, scores
   - Print a live-updating terminal summary (refresh every 2s)
4. **Add** `--live` flag to `capture_session.py` that enables the live monitor
5. Output format:
   ```
   ── GBaloot Live Monitor ──────────────────
   Session: hokum_aggressive_05 | Duration: 4m 32s
   WS Messages: 847 | Decoded: 712 (84%)

   Current Game: HOKUM ♠ | Round 2 | Trick 5/8
   Scores: Team A: 12 pts | Team B: 8 pts
   Match: 3 - 2

   Recent Events:
     [14:23:05] Card played: Seat 2 → J♠
     [14:23:03] Card played: Seat 1 → 10♠
     [14:23:01] Trick 4 won by Seat 3 (7 pts)
   ──────────────────────────────────────────
   ```

---

## Mission 6: Session Deduplication & Quality Scoring

**Priority**: 🟡 MEDIUM — Data hygiene
**Effort**: Small-Medium

### Problem
68 sessions were captured but only 8 had actual game data. Many captures overlap (same game captured from different reconnections), producing duplicate data that inflates session counts. Divergences can appear 3x because the same trick appears in 3 overlapping captures.

### What to Do
1. **Read** `gbaloot/core/session_manifest.py` — existing session tracking
2. **Read** `gbaloot/core/models.py` — `ProcessedSession` model
3. **Create** `gbaloot/core/session_quality.py`:
   ```python
   def score_session(session: ProcessedSession) -> SessionScore:
       """Rate session quality and data richness."""

   def deduplicate_sessions(sessions: list[ProcessedSession]) -> list[ProcessedSession]:
       """Remove overlapping captures of the same game."""
   ```
4. Quality scoring dimensions:
   - `completeness`: ratio of game events to total events (lobby/chat dilutes)
   - `trick_count`: more tricks = higher quality
   - `round_count`: complete rounds are more valuable
   - `decode_rate`: % of WS messages successfully decoded
   - `has_bidding`: captures that include bidding phase
   - `has_declarations`: captures with Baloot/Sawa declarations
5. Deduplication logic:
   - Match on: overlapping timestamps + same player names + same trick sequences
   - Keep the highest-quality capture, discard duplicates
   - Tag duplicates in the manifest rather than deleting them
6. **Integrate** into `run_benchmark.py` — deduplicate before comparing
7. **Write tests** with synthetic overlapping sessions

---

## Mission 7: Bidding Phase Validation

**Priority**: 🟡 MEDIUM — Expands benchmark to bidding logic
**Effort**: Medium

### Problem
The current benchmark focuses exclusively on the play phase (trick comparison). It ignores the bidding phase entirely. Validating bidding is important because:
- Bid outcomes determine game mode (SUN/HOKUM) and trump suit
- Our bidding engine should reach the same conclusions as the source

### What to Do
1. **Read** `gbaloot/core/bid_extractor.py` — existing bid extraction
2. **Read** `gbaloot/core/bid_comparator.py` — existing bid comparison logic
3. **Extend** bid comparison to verify:
   - Bid sequence: did each player's bid action match the source?
   - Bid outcome: is the final game mode and trump suit correct?
   - Bid timing: first-pass vs second-pass bidding round
4. **Add** bid agreement metrics to the scorecard:
   - `bid_outcome_accuracy`: % of rounds with matching mode/trump
   - `bid_sequence_accuracy`: % of individual bid actions matching
5. **Write tests** covering: SUN bid, HOKUM bid with trump selection, all-pass (re-deal), double/re-double

---

## Mission 8: GBaloot Test Coverage Expansion

**Priority**: 🟡 MEDIUM — Engineering quality
**Effort**: Medium

### Problem
GBaloot has 16 test files but coverage depth is unknown. Some modules (like `reconstructor.py`, `state_builder.py`, `match_analytics.py`) may have thin coverage.

### What to Do
1. **Run** `python -m pytest gbaloot/tests/ --tb=short -q` to see current baseline
2. **Read each test file** in `gbaloot/tests/` to assess coverage depth
3. **Read the corresponding source module** for each test file
4. **Identify gaps**: untested functions, missing edge cases, error paths
5. **Write new tests** targeting the weakest modules. Priority order:
   - `test_comparator.py` — the most critical module, needs edge case coverage
   - `test_trick_extractor.py` — extraction correctness is foundational
   - `test_point_tracker.py` — scoring verification
   - `test_decoder.py` — binary parsing edge cases
6. **Target**: every public function has at least one positive test and one error-path test
7. **Report** final test count and any modules that remain under-tested

---

## Mission 9: Benchmark Regression CI

**Priority**: 🟢 NICE-TO-HAVE — DevOps
**Effort**: Small-Medium

### Problem
After improving the engine or GBaloot pipeline, we need to re-run the benchmark to ensure agreement didn't regress. Currently this is manual.

### What to Do
1. **Read** `gbaloot/run_benchmark.py` — current benchmark runner
2. **Create** `gbaloot/tools/benchmark_regression.py`:
   - Store latest scorecard as the baseline (e.g., `data/baseline_scorecard.json`)
   - Run the benchmark and compare against the baseline
   - Report regressions: any metric that dropped
   - Report improvements: any metric that increased
   - Exit code: 0 if no regressions, 1 if any metric decreased
3. **Output format**:
   ```
   === Benchmark Regression Report ===
   Overall:       96.8% → 98.2% [+1.4%] ✅
   SUN:           94.4% → 96.3% [+1.9%] ✅
   HOKUM:         100%  → 100%  [=]      ✅
   Points:        100%  → 100%  [=]      ✅
   Tricks tested: 95    → 142   [+47]    ✅
   Result: PASS — No regressions
   ```
4. **Add** a workflow step to `/test` or create `/benchmark` workflow

---

## Mission 10: Strategic Ideas for the Project

These are high-value ideas that Claude should **think about** and **propose concrete implementations** for. Don't just describe — sketch out the architecture and key data structures.

### 10.1 Game Intelligence Reports
After each captured game, generate a structured **Game Intelligence Report**:
- Opening: what was bid, by whom, was it aggressive?
- Mid-game: which tricks were pivotal (high point swings)?
- Endgame: was Kaboot pursued? Was it successful?
- Player profiling: each player's tendencies (aggressive bidder, conservative player, trump-heavy)
- Use this data to train our bot's opponent modeling

### 10.2 Optimal Play Disagreement Analysis
When our engine and the source agree on the trick winner but our bot would have **played a different card**, that's an "optimal play disagreement". Track these to study whether our bot's card selection is strategically better or worse than what the source players chose.

### 10.3 Meta-Strategy Mining
Across many captured sessions, identify recurring patterns:
- What bid strategies lead to wins in SUN vs HOKUM?
- Which opening leads are most successful?
- Do aggressive bidders win more matches?
- Is there a dealer advantage?
- Feed these findings back into `ai_worker/strategies/` to improve the bot

### 10.4 Replay Simulation
Given a captured session, re-play it with our bot making the decisions instead of the original player. Compare outcomes:
- Would our bot have won the tricks that the source player won?
- Would it have bid differently?
- What's the "bot improvement delta" — how many more/fewer points would our bot score?

### 10.5 Cross-Platform Validation
GBaloot currently captures from one platform. The architecture should support capturing from multiple Baloot platforms (different platforms may use different protocols). Design a **protocol adapter layer** that abstracts the source-specific details (SFS2X, SignalR, REST) behind a common `GameEventStream` interface.

---

## Mission 11: Mobile Archive Retriever (🔴 HIGH PRIORITY)

**Priority**: 🔴 HIGH — Unlocks hundreds of complete games
**Effort**: Large (new module + pipeline integration)

### Context

The user has an extensive archive of completed games in the Source mobile app (Android, from Google Play). These archives contain **full game replays** — complete trick sequences with known winners, scores, and declarations. This is the single most valuable data source for benchmarking because:

- **Volume**: Hundreds of games vs. our current 8
- **Completeness**: Full games from start to finish (not partial captures mid-session)
- **Diversity**: SUN, HOKUM, Kaboot, Galoss, Baloot declarations — all game situations
- **Ground truth**: Source platform already computed the correct winners/scores

### The Plan

The user will capture the mobile app's API traffic using mitmproxy on their PC. When they browse their Archives in the app, the app makes HTTP/HTTPS requests to the backend to fetch game history. The user will save this captured traffic as a HAR file or mitmproxy flow file and place it in `gbaloot/data/archive_captures/`.

**Your job**: Write the code that parses this captured traffic, extracts game data, normalizes it into our session format, and feeds it into the benchmark pipeline.

### What to Do

#### Phase 1: Traffic Parser

1. **Read** `gbaloot/core/models.py` — understand `ProcessedSession` and event format
2. **Read** `gbaloot/core/decoder.py` — understand how live SFS2X capture is decoded
3. **Create** `gbaloot/tools/archive_retriever.py` — the main module with these functions:

```python
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ArchivedGame:
    """A single game retrieved from the source platform's archive API."""
    game_id: str
    mode: str                          # "SUN" or "HOKUM"
    trump_suit: Optional[str]          # "♠"|"♥"|"♦"|"♣" or None for SUN
    result: str                        # "win" | "loss" | "draw"
    players: list[dict]                # [{name, seat, team}, ...]
    tricks: list[dict]                 # [{cards: [...], winner_seat: int, points: int}, ...]
    declarations: list[dict]           # [{player_seat, type, trick_number}, ...]
    round_scores: dict                 # {"team1": int, "team2": int}
    match_scores: dict                 # {"team1": int, "team2": int}
    timestamp: str                     # ISO format
    raw_data: dict                     # Original API response for this game


@dataclass
class ArchiveParseResult:
    """Result of parsing captured API traffic."""
    games: list[ArchivedGame]
    total_requests: int
    game_requests: int
    parse_errors: list[str]
    source_format: str                 # "har" | "mitmproxy_flow" | "json_dump"


def parse_captured_traffic(capture_path: Path) -> ArchiveParseResult:
    """Parse captured mitmproxy/HAR traffic to extract archived games.

    Supports multiple capture formats:
    - HAR files (.har) from browser dev tools or mitmproxy
    - mitmproxy flow files (.flow) from mitmdump
    - Raw JSON dumps (.json) from manual API calls

    The function should:
    1. Detect the file format (HAR vs flow vs JSON)
    2. Extract HTTP responses that contain game data
    3. Parse each game response into an ArchivedGame
    4. Return all parsed games with error tracking
    """
    ...


def detect_api_endpoints(capture_path: Path) -> list[dict]:
    """Analyze captured traffic to identify archive-related API endpoints.

    This is a RECON function. Run it first on newly captured traffic to
    understand the API structure before writing game-specific parsers.

    Returns list of dicts:
    [
        {
            "url": "https://api.example.com/v1/games/history",
            "method": "GET",
            "params": {"page": "1", "size": "20"},
            "response_keys": ["games", "total", "page"],
            "sample_game_keys": ["gameId", "mode", "tricks", "result"],
            "count": 5,  # how many times this endpoint was hit
        },
        ...
    ]
    """
    ...


def archived_game_to_session(game: ArchivedGame) -> dict:
    """Convert an ArchivedGame to our ProcessedSession-compatible format.

    This bridges the archive data into the same format that
    GameComparator.compare_session_file() expects, so we can run
    the benchmark on archived games with zero pipeline changes.

    KEY MAPPING CONSIDERATIONS:
    - Archive data likely uses 1-indexed seats → convert to 0-indexed
    - Card representations may differ from SFS2X format → normalize
    - Trick structure must match ExtractedTrick expectations
    - Game mode names may differ (e.g., "hokom" vs "HOKUM") → normalize
    """
    ...


def retrieve_all_games(capture_dir: Path) -> list[ArchivedGame]:
    """Process all capture files in a directory and return all games.

    Deduplicates games by game_id (same game may appear in multiple
    capture files if the user browsed archives multiple times).
    """
    ...
```

#### Phase 2: API Auto-Requester (Fetch More Pages)

Once we understand the API structure, write a direct requester:

```python
def fetch_archive_page(
    base_url: str,
    auth_token: str,
    page: int,
    page_size: int = 20,
    headers: Optional[dict] = None,
) -> list[ArchivedGame]:
    """Fetch a single page of archived games directly from the API.

    The auth_token and base_url are discovered from the captured traffic.
    This function replicates exactly what the mobile app does.

    Use httpx (or requests) for HTTP calls.
    """
    ...


def fetch_all_archives(
    base_url: str,
    auth_token: str,
    max_pages: int = 50,
    headers: Optional[dict] = None,
) -> list[ArchivedGame]:
    """Paginate through the entire archive, fetching all available games.

    - Start from page 1, fetch until no more results or max_pages reached
    - Rate limit: 1 request per second (don't hammer the API)
    - Save each page's raw response to gbaloot/data/archive_captures/
    - Track and report progress
    - Handle auth expiry gracefully
    """
    ...
```

#### Phase 3: Pipeline Integration

```python
def run_archive_benchmark(archive_dir: Path) -> dict:
    """Run the full benchmark pipeline on archived games.

    1. Parse all capture files in archive_dir
    2. Convert each ArchivedGame to ProcessedSession format
    3. Feed into GameComparator
    4. Generate scorecard
    5. Return combined results

    This is the CLI entry point — can be run as:
    python -m gbaloot.tools.archive_retriever --dir gbaloot/data/archive_captures/
    """
    ...
```

#### Phase 4: CLI Interface

Add a CLI entry point to `archive_retriever.py`:

```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GBaloot Archive Retriever")
    subparsers = parser.add_subparsers(dest="command")

    # Command: detect — analyze captured traffic
    detect = subparsers.add_parser("detect", help="Detect API endpoints in captured traffic")
    detect.add_argument("capture_file", type=Path)

    # Command: parse — extract games from captured traffic
    parse = subparsers.add_parser("parse", help="Parse games from captured traffic")
    parse.add_argument("capture_file", type=Path)
    parse.add_argument("--output", type=Path, default=Path("gbaloot/data/archive_sessions/"))

    # Command: fetch — actively fetch archive pages from API
    fetch = subparsers.add_parser("fetch", help="Fetch archive pages from API")
    fetch.add_argument("--config", type=Path, help="API config JSON (from detect output)")
    fetch.add_argument("--token", type=str, help="Auth token")
    fetch.add_argument("--pages", type=int, default=50)
    fetch.add_argument("--output", type=Path, default=Path("gbaloot/data/archive_captures/"))

    # Command: benchmark — run benchmark on archived games
    bench = subparsers.add_parser("benchmark", help="Run benchmark on archived games")
    bench.add_argument("--dir", type=Path, default=Path("gbaloot/data/archive_captures/"))

    args = parser.parse_args()
    # ... dispatch to appropriate function
```

### Expected Data Shapes

The archive API will likely return game data in one of these structures. Be prepared to handle all of them:

**Shape A: Flat game list**
```json
{
  "games": [
    {
      "gameId": "12345",
      "gameMode": 2,
      "trumpSuit": 0,
      "result": 1,
      "players": [
        {"name": "Player1", "seat": 1, "score": 15},
        {"name": "Player2", "seat": 2, "score": 11}
      ],
      "rounds": [
        {
          "tricks": [
            {"cards": [38, 36, 32, 45], "winner": 3, "points": 7},
            ...
          ],
          "score": {"team1": 15, "team2": 11}
        }
      ]
    }
  ],
  "total": 250,
  "page": 1
}
```

**Shape B: Game summary + detail endpoint**
```json
// List endpoint: /api/games/history?page=1
{
  "items": [
    {"id": "12345", "mode": "hokom", "date": "2026-02-15", "result": "win"},
    ...
  ]
}

// Detail endpoint: /api/games/12345/replay
{
  "id": "12345",
  "events": [
    {"type": "bid", "player": 1, "action": "hokom", "suit": 0},
    {"type": "play", "player": 2, "card": 38},
    {"type": "trick_won", "winner": 3, "points": 7},
    ...
  ]
}
```

**Shape C: Compact binary/encoded**
The response might use SFS2X-style encoding even over HTTP. If so, reuse the existing `SFS2XDecoder`.

### Critical Implementation Notes

1. **Auth tokens expire** — the fetcher must handle 401 responses and prompt for a new token
2. **Rate limiting** — never hit the API faster than 1 req/sec. Add `time.sleep(1)` between fetches
3. **Idempotency** — if the user runs the fetcher twice, don't create duplicate game files
4. **Card index mapping** — archive data may use the same 0-51 index system as SFS2X. Reuse `card_mapping.py`
5. **Seat indexing** — archive data likely uses 1-indexed seats. Convert to 0-indexed for our engine
6. **Save raw responses** — always save the raw API response alongside the parsed data, for debugging

### Acceptance Criteria

- [ ] `detect_api_endpoints()` successfully identifies archive API from captured HAR/flow file
- [ ] `parse_captured_traffic()` extracts games from at least one capture format
- [ ] `archived_game_to_session()` produces data compatible with `GameComparator`
- [ ] `fetch_all_archives()` can paginate through multi-page archives with rate limiting
- [ ] CLI works for all 4 commands: detect, parse, fetch, benchmark
- [ ] All games saved as individual JSON files in `gbaloot/data/archive_sessions/`
- [ ] Tests in `gbaloot/tests/test_archive_retriever.py` (at least 5 test cases)
- [ ] Running the benchmark on archived games produces a valid scorecard

### Files to Read Before Starting
| File | Why |
|------|-----|
| `gbaloot/core/models.py` | ProcessedSession format that comparator expects |
| `gbaloot/core/comparator.py` | How sessions are compared — your output must match its input |
| `gbaloot/core/card_mapping.py` | Card index ↔ Card object conversion (reuse this!) |
| `gbaloot/core/trick_extractor.py` | ExtractedTrick format for comparison |
| `gbaloot/run_benchmark.py` | How the benchmark is orchestrated |
| `gbaloot/docs/archive_retrieval_guide.md` | User-facing setup guide (read for full context) |

---

## How Claude Should Work

### Before Starting a Mission
1. **Read this file** for context
2. **Read the files listed** in the mission's "What to Do" section
3. **Read `CLAUDE.md`** if you haven't already (project-wide conventions)
4. Run existing tests to see current baseline

### While Working
- Write clean, documented Python code following project conventions
- Use `from __future__ import annotations` at the top of every file
- Use dataclasses for structured outputs
- Wrap risky operations in try/except with logging
- Create or update tests for every code change

### After Finishing
- Run `python -m pytest gbaloot/tests/ --tb=short -q` — all tests must pass
- If you modified the benchmark pipeline, re-run `python gbaloot/run_benchmark.py`
- Provide a brief summary of what you did and what the results were
- Flag any issues or follow-up work you identified

### What NOT to Do
- Don't modify `game_engine/` files — GBaloot reads from the engine, not writes
- Don't modify `CLAUDE.md` — that's project-level, not GBaloot-specific
- Don't break existing test baselines without justification
- Don't add external dependencies beyond Python stdlib + existing requirements
- Don't use the word "Kammelna" in code — use "Source" or "source platform"
- Don't create classes where a pure function would suffice
