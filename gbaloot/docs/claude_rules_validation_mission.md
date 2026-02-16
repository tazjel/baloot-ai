# Mission: Full Baloot Rules Validation & Strategy Insights

> **Priority**: CRITICAL — Our trick resolution is 100% validated. Now verify EVERY other rule.
> **Prerequisite**: Mission "Mobile Archive Parser" (completed — 100% trick agreement on 109 archives).
> **Goal**: Audit ALL game phases beyond trick resolution. Validate scoring, bidding, declarations, Kaboot, Khasara, Qayd, and game-ending conditions against the 109 real archive replays. Extract strategic insights from highlight images.

---

## 0. ⚡ STOP — Answer These Questions First

> **Before writing a single line of code, answer every question below.**
> Think deeply. Show your reasoning. The smartest path is rarely the most obvious one.
> Save your answers to `gbaloot/docs/rules_validation_strategy.md` before proceeding.

### 🔍 Data Intelligence — What Do We Actually Have?

1. **Data Inventory**: Open 3-5 random archive files and examine them thoroughly. What event types (`e=`) are present? Are there events we haven't documented? List every unique `e=` value you find across the samples and what each one contains.

2. **e=12 Completeness Check**: Does every round in every archive have an `e=12` result event? Or are some games incomplete (abandoned, disconnected)? How will you handle incomplete games — skip silently, or flag them?

3. **e1/e2 Semantics Puzzle**: The `e1`/`e2` fields in the `e=12` event — do they include the 10-point last-trick bonus or not? 
   - In HOKUM: if `e1 + e2 == 162` → includes bonus. If `== 152` → excludes it.
   - In SUN: if `e1 + e2 == 130` → includes bonus. If `== 120` → excludes it.
   - **Check 10+ rounds across different games to be sure.** This single assumption determines whether your entire Card Abnat validator is correct or off-by-10 on every round.

4. **p1/p2 Semantics Puzzle**: Are `p1`/`p2` in Abnat (raw points) or Game Points (GP)? What about `s1`/`s2` — cumulative Abnat or cumulative GP? If you get this wrong, every comparison will fail. **Prove your answer with arithmetic from 3+ sample rounds.**

5. **Declaration Data Richness**: Look at `e=3` events. Is `prjC` (project cards bitmask) always present? Can you decode it to recover the actual cards in each declaration? That would let us validate project detection, not just scoring.

6. **Undocumented Fields**: Are there any fields in `e=12` that we haven't mapped yet? (e.g., sawa-related flags, qayd penalties, open/closed variant indicators). List them all — they might be validation gold.

### 🧠 Architecture — What's the Smartest Build Order?

7. **One Validator or Three?** I described 3 separate validators (scoring, bidding, declarations). But most of the data lives in `e=12` round results + `e=2` bidding + `e=3` declarations — all events in the same file. Would a **single unified round-parser** that extracts everything in one pass be smarter? Or does separation give better testability? Argue both sides, then decide.

8. **Engine Coupling vs Independence**: Should the validators call our actual engine code (e.g., import `ScoringEngine` and run it) or should they implement the rules independently from scratch?
   - **Coupled approach**: Import the engine, feed it archive data, compare output. Pro: tests the real code. Con: if the engine is wrong, both sides agree and you miss the bug.
   - **Independent approach**: Reimplement scoring math from the constants. Pro: true independent validation. Con: more code, could have its own bugs.
   - **Hybrid**: Use independent math for card abnat (simple), but call the engine for complex rules like Khasara/doubling? 
   - **Which approach gives us the highest confidence per line of code written?**

9. **Quick Win Triage**: Which validations can you complete in under 20 lines of code each, and which require serious engineering? Rank all validation targets by (effort required) vs (confidence gained). What's the 80/20 — which 20% of work gives 80% of the validation confidence?

10. **Existing Code Reuse**: The `archive_parser.py` and `archive_trick_extractor.py` already parse archives and extract tricks. How much of that can you reuse? Can you extend `archive_trick_extractor.py` to also extract bidding and scoring data, or would that bloat it?

### 🎯 Validation Strategy — How Do We Know If We're Right?

11. **Ground Truth Hierarchy**: If our engine says one thing and the archive says another, we assume the archive is right. But what if the archive has a bug? How would we detect a Kammelna engine bug vs our bug? (Hint: check if the archive's own numbers are internally consistent — does `e1 + e2` always equal the expected total? Do `s1/s2` accumulate correctly?)

12. **Statistical vs Exhaustive**: Do we need to validate ALL 1,095 rounds, or can we validate a stratified sample (e.g., 50 HOKUM rounds, 50 SUN, 10 Kaboot, 10 doubled, 10 with declarations) and extrapolate? What's the risk of sampling vs exhaustive?

13. **Divergence Response Plan**: If you find divergences, what's the triage protocol?
    - A. Data parsing bug (our parser misread the archive)
    - B. Mapping bug (index/suit conversion error)
    - C. Genuine rule difference (our engine implements a rule differently)
    - D. Kammelna bug (the archive data is internally inconsistent)
    - How will you distinguish A-D quickly?

14. **Edge Case Hunting**: Which edge cases are most likely to expose bugs?
    - Kaboot rounds (extreme: one team gets 0)
    - Gahwa rounds (flat 152, overrides everything)
    - Rounds with both Khasara AND declarations
    - Rounds with Baloot AND doubling (immunity test)
    - Rounds where GP rounding tiebreak fires
    - **Can you find at least one example of each in the 109 archives?**

### 📊 Highlight Images — Are They Worth It?

15. **Image Value Assessment**: Before spending time on all 9 images, read 2-3 of them. Are they actual statistical charts with numbers we can extract? Or are they decorative achievement badges? If they're just badges, skip the image analysis and focus on computing our own statistics from the raw archive data — that would be far more valuable.

16. **Statistics From Raw Data vs Screenshots**: If we can compute bidding strength, Kaboot rate, Khasara rate, and declaration frequency directly from the 109 archive files, do we even need the highlight images? The raw data gives us exact numbers; the images give us approximate visual reads. **Which source produces better AI strategy insights?**

### 🏗️ Execution Plan — Show Me Your Battle Plan

17. **Proposed Execution Order**: Based on your answers above, write your execution plan as a numbered checklist. Include estimated time per step. If you think any of my Phase 1-4 should be reordered, merged, split, or dropped — say so and explain why.

18. **Definition of Done**: For each validation category, what specific output proves it's validated? (Examples: "Card abnat: a CSV showing archive e1/e2 vs computed values for all 1,095 rounds, with 0 divergences" or "Kaboot: list of all rounds with kbt flag, confirming trick count = 8-0 for each")

19. **Failure Mode**: What's your plan if >5% of rounds show divergences? Do you stop and investigate, or complete the full run and analyze patterns? (Hint: patterns in where divergences cluster — by game mode, by archive file, by round number — are often more diagnostic than individual divergences.)

---

> **When you've answered all 19 questions, THEN proceed to Section 3 (What To Build).**
> Your answers will determine the actual architecture — Section 3 is a starting suggestion, not a mandate.

---

## 1. Context & Current State

### What We've Already Proven (DO NOT REDO)
- **8,107 tricks** across **1,095 rounds** from **109 real game archives** — **100% trick winner agreement** ✅
- Trick resolution logic (`get_trick_winner_index()`) is verified identical to Kammelna
- Card mapping, player indexing, trump suit encoding — all verified
- Leader chain (trick N+1 leader = trick N winner) — 100% validated

### What This Mission Must Validate
Everything else:

| Phase | Engine File | Key Rules To Verify |
|-------|-----------|---------------------|
| Bidding | `bidding_engine.py` | 2-round auction, Gablak interruption, All-Pass redeal, Kawesh (zero-point hand) |
| Doubling | `doubling_handler.py` | Double→Triple→Four→Gahwa chain, Sun Firewall rule, team constraints |
| Variant Selection | `doubling_handler.py` | OPEN/CLOSED for Hokum, Gahwa forces OPEN |
| Legal Play | `validation.py` | 16+ suit-following rules, trump obligation, cut rules |
| Declarations | `project_manager.py`, `projects.py` | Sira (3-seq=20), 50 (4-seq=50), 100 (5+seq or 4-of-a-kind=100), 400 (4 Aces SUN=200), hierarchy/tiebreaks |
| Baloot | `baloot_manager.py` | K+Q of trump, 2 GP always immune to doubling, blocked by 100-project containing K+Q |
| Scoring | `scoring_engine.py` | Abnat→GP conversion, rounding rules, tiebreaks, total GP constraint (SUN=26, HOKUM=16) |
| Kaboot | `scoring_engine.py` | All 8 tricks by one team, SUN=44 GP, HOKUM=25 GP |
| Khasara | `scoring_engine.py` | Bidder loses → all points go to opponent |
| Doubling Multiplier | `scoring_engine.py` | ×2/×3/×4 applied to score, Gahwa=152 flat |
| Sawa | `sawa_manager.py`, `sawa.py` | Grand slam guarantee, trump control check in Hokum |
| Akka | `akka_manager.py`, `akka.py` | Boss card in HOKUM, non-trump, non-Ace, highest remaining |
| Qayd | `qayd_engine.py` | Forensic challenge flow, penalties |
| Match End | `constants.py` | First team to 152 GP wins the match |

---

## 2. The Archive Data You'll Use

### Game Replays (109 files)
**Location**: `gbaloot/data/archive_captures/kammelna_export/savedGames/*.json`

Each file contains complete game replays with event arrays. The format is fully documented in `gbaloot/docs/claude_mobile_archive_mission.md`. **READ THAT FILE FIRST.**

#### Key Events for This Mission (beyond trick resolution)

**Bidding events (e=2):**
```json
{"p": 1, "e": 2, "b": "pass", "ts": 4, "rb": -1}
{"p": 4, "e": 2, "b": "hokom", "gm": 2, "ts": 4, "rb": 4}
{"p": 1, "e": 2, "b": "sun", "gm": 1, "ts": 4, "rb": 1}
{"p": 3, "e": 2, "b": "hokom2", "gm": 2, "ts": 4, "rb": 3}    // Second-round bid
{"p": 4, "e": 2, "b": "triple", "gm": 2, "gem": 2, "rd": 4, "ts": 3, "rb": 4}  // Doubling
{"p": 1, "e": 2, "b": "hokomclose", "gm": 2, "gem": 1, "rd": 1, "ts": 3, "rb": 4, "hc": 1}  // Variant
```

| Bid `b` Value | Meaning |
|---------------|---------|
| `pass` | Pass |
| `hokom` | Hokum bid (Round 1 — takes floor card suit) |
| `sun` | Sun bid |
| `hokom2` | Hokum bid (Round 2 — choose own suit) |
| `thany` | Second player counter-bid |
| `clubs`, `diamonds`, `hearts`, `spades` | Explicit suit bid (Round 2) |
| `double` | Double (×2) |
| `triple` | Triple (×3) |
| `hokomclose` / `hokomopen` | Variant selection (CLOSED/OPEN) |
| `wala` | All-pass / Pass in Round 2 |

| Bid Field | Meaning |
|-----------|---------|
| `gm` | Game mode: 1=SUN, 2=HOKUM |
| `ts` | Trump suit: 1=♠, 2=♣, 3=♦, 4=♥ |
| `rb` | Round bidder (-1 = nobody) |
| `gem` | Escalation multiplier (2=Double, 3=Triple) |
| `rd` | Re-doubler player index |
| `hc` | Hokom close flag (1=CLOSED variant) |

**Declaration events (e=3):**
```json
{"p": 1, "e": 3, "prj": 1}           // Sira declaration
{"p": 4, "e": 3, "prj": 5}           // 50 declaration (3-of-a-kind)
{"p": 4, "e": 3, "prj": 6}           // 100 declaration (4-of-a-kind)
{"p": 4, "e": 3, "prjC": 3584}       // Project cards bitmask (for validation)
```

| `prj` Value | Declaration Type | Abnat Score |
|-------------|-----------------|-------------|
| 1 | Sira (3-sequence) | 20 |
| 5 | 50 (4-sequence) | 50 |
| 6 | 100 (5+seq or 4-of-a-kind) | 100 |

**Round Result events (e=12) — THE GOLD STANDARD:**
```json
{
  "e": 12,
  "rs": {
    "p1": 47,         // Team 1 TOTAL round points (cards + declarations)
    "p2": 135,        // Team 2 TOTAL round points
    "e1": 47,         // Team 1 raw card points earned (Abnat)
    "e2": 105,        // Team 2 raw card points earned
    "r1": [],         // Team 1 declarations: [{"n":"sira","val":"20"}, {"n":"baloot","val":"20"}]
    "r2": [{"n":"sira","val":"20"}],
    "m": 2,           // Mode: 1=SUN, 2=HOKUM
    "em": 3,          // Escalation multiplier (1=normal, 2=double, 3=triple)
    "w": 2,           // Winner of this round (team 1 or 2)
    "b": 2,           // Bidder team
    "s1": 5,          // Team 1 CUMULATIVE match score after this round
    "s2": 13,         // Team 2 CUMULATIVE match score
    "kbt": 1,         // Kaboot flag (present = kaboot happened)
    "lr": 1,          // Last round flag
    "lmw": 2          // Last match winner
  }
}
```

### Highlight Images (9 PNG files)
**Location**: `gbaloot/data/archive_captures/kammelna_export/highlights/`

These are **PNG screenshot images** (not structured data) of statistical summaries from the mobile app:

| File | Content Description |
|------|---------------------|
| `bidStrength` | Visual chart of bidding strength distribution |
| `catchings` | Statistics on catch plays (taking tricks with high cards) |
| `cheatings` | Visual data on Qayd/cheat events detected |
| `kaboot` | Kaboot (fold/shutout) frequency and patterns |
| `lostBid` | Analysis of rounds where the bidder lost (Khasara) |
| `picWithAce` | Ace-pickup strategy visualization |
| `projectsScores` | Declaration scoring patterns across games |
| `tensHunt` | 10-hunting strategy data (capturing 10-point cards) |
| `wonBid` | Won bid analysis and patterns |

**Task**: Use your vision capabilities to read these PNG images and extract the statistical insights they contain. Each image is approximately 512×512 pixels.

---

## 3. What To Build

### Phase 1: Scoring Validator (`gbaloot/tools/archive_scoring_validator.py`)

Build a tool that walks every round in all 109 archives and validates our scoring engine's calculations against the `e=12` round result.

```python
"""
Archive Scoring Validator
=========================
Validates our scoring engine's rules against 109 real archive round results.

For each round, compares:
1. Card abnat (e1/e2) against engine-computed trick points
2. Declaration scoring (r1/r2) against project detection
3. Total round points (p1/p2) against engine calculation
4. Kaboot detection (kbt flag) against trick count
5. Khasara logic (bidder loses → all points to opponent)
6. Doubling multiplier (em) application
7. Cumulative match scores (s1/s2) progression
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json

@dataclass
class ScoringDivergence:
    """Records a scoring mismatch between archive and engine."""
    archive_file: str
    round_index: int
    category: str        # 'card_abnat', 'declaration', 'kaboot', 'khasara', 'total_points', 'cumulative', 'multiplier'
    expected: any        # Value from archive (ground truth)
    computed: any        # Value from engine
    details: str         # Human-readable explanation

@dataclass
class ScoringValidationResult:
    """Complete validation results for one archive file."""
    archive_file: str
    rounds_validated: int
    divergences: List[ScoringDivergence] = field(default_factory=list)
    
    @property
    def is_clean(self) -> bool:
        return len(self.divergences) == 0

def validate_archive_scoring(archive_path: Path) -> ScoringValidationResult:
    """
    Validate all scoring rules against one archive file.
    
    Steps per round:
    1. Parse bidding events → determine game_mode, trump_suit, bidder_team, multiplier
    2. Parse card plays → compute card abnat per team using POINT_VALUES_SUN/HOKUM
    3. Include last trick bonus (10 abnat)
    4. Parse declaration events → validate against project detection
    5. Compute total round points
    6. Check Kaboot (one team won all 8 tricks)
    7. Check Khasara (bidder team got fewer points)
    8. Apply doubling multiplier
    9. Compare against e=12 round result
    """
    pass  # IMPLEMENT THIS

def validate_all_archives(archive_dir: Path) -> Dict:
    """
    Validate scoring across all 109 archives.
    
    Returns a summary report:
    {
        'total_archives': 109,
        'total_rounds': int,
        'clean_archives': int,
        'divergences_by_category': {
            'card_abnat': int,
            'declaration': int,
            'kaboot': int,
            'khasara': int,
            'total_points': int,
            'cumulative': int,
            'multiplier': int
        },
        'details': [ScoringValidationResult, ...]
    }
    """
    pass  # IMPLEMENT THIS
```

#### Scoring Rules You Must Implement Precisely

**A. Card Point Calculation (Abnat)**

Use these point tables from `game_engine/models/constants.py`:

```python
# SUN mode — all suits equal, no trump
POINT_VALUES_SUN = {'7': 0, '8': 0, '9': 0, 'J': 2, 'Q': 3, 'K': 4, '10': 10, 'A': 11}
# Total per round: 120 card points + 10 last trick = 130 Abnat

# HOKUM mode — trump suit uses these values, side suits use SUN values  
POINT_VALUES_HOKUM = {'7': 0, '8': 0, 'Q': 3, 'K': 4, '10': 10, 'A': 11, '9': 14, 'J': 20}
# Trump suit total: 62 Abnat (J=20, 9=14, A=11, 10=10, K=4, Q=3)
# Per side suit: 30 Abnat each (A=11, 10=10, K=4, Q=3, J=2)
# Total per round: 62 + 3*30 = 152 card points + 10 last trick = 162 Abnat
```

For each trick, sum the card points won by the winning team. Add 10 Abnat to whoever wins trick 8 (last trick bonus).

**B. Abnat → Game Points Conversion**

```
HOKUM: Game Points = Abnat / 10, rounded to nearest integer
  - If decimal > 0.5 → round UP
  - If decimal <= 0.5 → round DOWN
  - Total GP per round MUST equal exactly 16 (from cards only)
  
SUN: Game Points = (Abnat × 2) / 10, rounded to nearest integer
  - If decimal >= 0.5 → round UP (NOTE: >= not > for SUN!)
  - If decimal < 0.5 → round DOWN
  - Total GP per round MUST equal exactly 26 (from cards only)
```

**TIEBREAK**: If rounding causes GP total to not equal 16 (HOKUM) or 26 (SUN), the difference is assigned to the NON-bidder team.

**C. Kaboot**
- If one team wins ALL 8 tricks: **Kaboot**
- Kaboot GP: SUN = **44**, HOKUM = **25** (flat, replaces normal GP calculation)
- The `kbt` flag in `e=12` events indicates Kaboot

**D. Khasara (Bidder Loses)**
- If bidder team's GP ≤ opponent team's GP → **Khasara**
- All GP (both teams' share) goes to the opponent
- Score becomes: Bidder = 0, Opponent = Total GP

**E. Doubling Multiplier (Gahwa Chain)**

| Level | Multiplier | Applied To |
|-------|-----------|-----------|
| Normal (1) | ×1 | — |
| Double (2) | ×2 | Final GP after Khasara |
| Triple (3) | ×3 | Final GP after Khasara |
| Four (4) | ×4 | Final GP after Khasara |
| Gahwa (100) | Flat 152 | Winner gets 152, loser gets 0 |

**F. Baloot Declaration (K+Q of Trump)**
- Worth 2 GP per declaration, always
- **IMMUNE to doubling** — added AFTER multiplier is applied
- Only in HOKUM mode (where trump exists)
- Blocked if the player declared a 100-project containing K+Q, or 4-Kings/4-Queens project

**G. Declaration Points**

| Type | Abnat | GP (HOKUM, ÷10) | GP (SUN, ×2÷10) |
|------|-------|----------------|----------------|
| Sira (3-seq) | 20 | 2 | 4 |
| 50 (4-seq) | 50 | 5 | 10 |
| 100 (5+seq or 4-kind) | 100 | 10 | 20 |
| 400 (4 Aces, SUN only) | 200 | — | 40 |

Declarations are added to GP **before** Khasara check, but **not** affected by doubling.

Wait — let me re-check the engine code. Looking at `scoring_engine.py`:

```python
# Lines 170-179: Project GP added AFTER kaboot/normal calculation
proj_gp_us = project_abnat_us // 10  # HOKUM
proj_gp_us = (project_abnat_us * 2) // 10  # SUN
game_points_us += proj_gp_us

# Lines 184-206: Khasara check uses score_us/score_them (which INCLUDES project GP)
# Lines 208-220: Doubling multiplier applied to score_us/score_them (which INCLUDES project GP)
# Lines 222-238: Baloot GP added AFTER doubling
```

So the actual order is:
1. Card abnat → GP
2. Add declaration GP
3. Check Khasara (on total including declarations)
4. Apply doubling multiplier (applies to everything including declarations)
5. Add Baloot GP (immune to doubling)

**VERIFY THIS ORDER AGAINST THE ARCHIVE DATA.**

---

### Phase 2: Bidding Validator (`gbaloot/tools/archive_bidding_validator.py`)

Validate bidding rules extracted from `e=2` events:

```python
"""
Bidding Rules to Validate:
1. Turn order: Player to dealer's left bids first (dealer_index+1 % 4)
2. Round 1: Each player gets exactly one chance to bid or pass
3. If Round 1 winner exists → doubling phase
4. If all pass Round 1 → Round 2 begins (different suit options available)
5. If all pass Round 2 → redeal (same dealer)
6. Kawesh: Hand with only 7,8,9 → redeal
7. Gablak: Interruption window after Round 1 buyer is tentative
8. Sun bids override Hokum bids
9. Ashkal: Partner can call Sun on behalf of team
"""

@dataclass
class BiddingValidationResult:
    archive_file: str
    rounds_validated: int
    all_pass_count: int       # How many rounds were all-pass redeals
    hokum_count: int
    sun_count: int
    doubled_count: int
    tripled_count: int
    kawesh_count: int
    issues: List[str]
```

#### Bidding Insights to Extract

From the 109 archives, compute these statistics:
- % of rounds HOKUM vs SUN
- % of rounds that go to Round 2
- % of all-pass redeals
- Distribution of doubling chain depth (normal/double/triple/four/gahwa)
- OPEN vs CLOSED variant distribution (for Hokum)
- Average bidder position relative to dealer

---

### Phase 3: Declaration Validator (`gbaloot/tools/archive_declaration_validator.py`)

Cross-reference `e=3` events against `e=12` round results:

```python
"""
Validate:
1. All declarations in e=3 events appear in e=12.rs.r1/r2
2. Declaration scores match expected values (Sira=20, 50=50, 100=100)
3. Declaration resolution (winner-takes-all when both teams declare)
4. Declarations added correctly to round points
5. Baloot declarations tracked in e=12 (look for {"n":"baloot","val":"20"})
"""
```

---

### Phase 4: Highlight Image Analysis

Use your vision capabilities to read each PNG file and extract insights:

**Files**: `gbaloot/data/archive_captures/kammelna_export/highlights/`

For each image, produce a structured analysis:

```markdown
### bidStrength Analysis
- [Description of what the chart shows]
- [Key statistics visible]
- [Strategic implications for our AI]

### catchings Analysis  
- [Description]
- [Key patterns in card-catching behavior]

### cheatings Analysis
- [Qayd/cheating event frequency]
- [Most common violation types]

### kaboot Analysis
- [Kaboot frequency and conditions]
- [Which modes produce more Kaboots]

### lostBid Analysis
- [How often the bidder loses (Khasara rate)]
- [Correlation with bid type/suit]

### picWithAce Analysis
- [Ace-pickup patterns]

### projectsScores Analysis
- [Declaration frequency]
- [Most profitable declaration types]

### tensHunt Analysis
- [10-point card hunting strategies]
- [Success rate of 10-hunting]

### wonBid Analysis
- [Win rate by bid type]
- [Correlation with hand strength]
```

Save the full analysis to: `gbaloot/docs/strategy_insights_report.md`

---

## 4. Existing Files You Must Study

| File | Purpose | Your Interaction |
|------|---------|-----------------|
| `gbaloot/docs/claude_mobile_archive_mission.md` | **READ FIRST** — Complete archive format documentation | Reference |
| `gbaloot/tools/archive_parser.py` | Existing parser (already built) | **REUSE** parsing logic |
| `gbaloot/tools/archive_trick_extractor.py` | Existing extractor (already built) | **REUSE** extraction logic |
| `gbaloot/tools/run_archive_benchmark.py` | Existing benchmark runner | **EXTEND** or model new validators on this |
| `game_engine/logic/scoring_engine.py` | Scoring logic to validate | **STUDY** — this IS the implementation you're auditing |
| `game_engine/logic/bidding_engine.py` | Bidding logic | **STUDY** |
| `game_engine/logic/doubling_handler.py` | Doubling chain logic | **STUDY** |
| `game_engine/logic/project_manager.py` | Declaration handling | **STUDY** |
| `game_engine/logic/baloot_manager.py` | K+Q trump declaration | **STUDY** |
| `game_engine/logic/validation.py` | Legal move validation | **STUDY** |
| `game_engine/logic/rules/projects.py` | Pure project detection logic | **REUSE** for declaration validation |
| `game_engine/logic/rules/akka.py` | Akka eligibility | Reference |
| `game_engine/logic/rules/sawa.py` | Sawa eligibility | Reference |
| `game_engine/models/constants.py` | Point values, rank orders, GP totals | **IMPORT** constants |

---

## 5. Existing Tests You Should Know About

There are 50+ existing test files. The most relevant ones:

| Test File | What It Covers |
|-----------|---------------|
| `tests/game_logic/test_scoring_engine.py` | Scoring calculations |
| `tests/game_logic/test_scoring_comprehensive.py` | Comprehensive scoring scenarios |
| `tests/game_logic/test_scoring_integration.py` | Integration scoring tests |
| `tests/game_logic/test_bidding_integration.py` | Bidding flow |
| `tests/game_logic/test_bidding_edge_cases.py` | Edge case bidding |
| `tests/game_logic/test_doubling_handler.py` | Doubling chain |
| `tests/game_logic/test_contract_handler.py` | Contract finalization |
| `tests/game_logic/test_project_manager.py` | Declaration management |
| `tests/game_logic/test_baloot_declaration.py` | Baloot K+Q |
| `tests/game_logic/test_akka_manager.py` | Akka boss card |
| `tests/game_logic/test_sawa_manager.py` | Sawa grand slam |
| `tests/game_logic/test_validation.py` | Legal move rules |
| `tests/features/test_sun_kaboot.py` | Sun Kaboot |
| `tests/features/test_project_scoring.py` | Project scoring |
| `tests/features/test_mashaari.py` | Mashaari declarations |

**DO NOT BREAK EXISTING TESTS.** Run them after any changes.

---

## 6. Scoring Engine Deep Dive — The Precise Algorithm

Here is the exact scoring algorithm from `scoring_engine.py` that you must validate:

```
Input: round_history (list of 8 tricks), declarations, bid info, doubling_level

Step 1: Card Abnat
  For each trick in round_history:
    Sum card point values for winning team
  Add 10 abnat to team that won trick 8 (last trick bonus)

Step 2: Project Abnat
  Sum declaration scores per team

Step 3: Check Kaboot
  Count tricks won by each team
  If one team has 0 tricks → Kaboot
    SUN: winner gets 44 GP (cards only)
    HOKUM: winner gets 25 GP (cards only)
  Else:
    Calculate GP from card abnat + last trick bonus
    Apply rounding + tiebreak

Step 4: Add Declaration GP
  HOKUM: declaration_abnat // 10
  SUN: (declaration_abnat * 2) // 10
  Added to BOTH kaboot and normal results

Step 5: Khasara Check  
  If NOT sawa_failed AND NOT kaboot:
    If bidder team GP <= opponent GP → Khasara
    Total pot goes to opponent, bidder gets 0
  If sawa_failed → automatic Khasara for sawa claimer's team

Step 6: Doubling Multiplier
  If level >= 100 (Gahwa): winner gets 152, loser gets 0
  If level >= 2: score *= level (2, 3, or 4)

Step 7: Baloot GP (IMMUNE to doubling)
  Add 2 GP per valid Baloot declaration (K+Q of trump)
  Added AFTER multiplier
```

### Known Edge Cases in Scoring

1. **Rounding asymmetry**: SUN uses `>= 0.5` for rounding, HOKUM uses `> 0.5`
2. **GP total mismatch fix**: If rounding causes GP total ≠ 16/26, the difference is added to/subtracted from the NON-bidder team
3. **Kaboot + Declarations**: Even in Kaboot, declarations still count (added on top)
4. **Khasara includes declarations**: Declaration GP is included in the Khasara pot
5. **Gahwa overrides everything**: Winner gets exactly 152 (match target), regardless of other calculations
6. **Baloot is the only thing truly immune**: Added post-multiplier

---

## 7. Card Abnat Validation Formula

For each round, you can validate `e1` and `e2` from the `e=12` result by computing:

```python
def compute_card_abnat(tricks, game_mode, trump_suit):
    """
    tricks: list of (cards_played, winner_team) from archive
    game_mode: 'SUN' or 'HOKUM'
    trump_suit: suit symbol for HOKUM mode
    """
    abnat = {'team1': 0, 'team2': 0}
    
    for i, (cards, winner_team) in enumerate(tricks):
        trick_points = 0
        for card in cards:
            if game_mode == 'HOKUM' and card.suit == trump_suit:
                trick_points += POINT_VALUES_HOKUM[card.rank]
            else:
                trick_points += POINT_VALUES_SUN[card.rank]
        abnat[winner_team] += trick_points
    
    # Last trick bonus
    _, last_winner = tricks[-1]
    abnat[last_winner] += 10
    
    return abnat
```

**Validation**: `compute_card_abnat()` result must match `e1`/`e2` in the archive's `e=12` event.

**IMPORTANT NOTE**: The archive's `e1`/`e2` values represent raw card points (abnat) **WITHOUT** last trick bonus. The `p1`/`p2` values are the final round scores. Verify this assumption against the data — if `e1 + e2 != 152` (HOKUM) or `e1 + e2 != 120` (SUN), then last trick bonus IS included.

---

## 8. File Structure to Create

```
gbaloot/
├── tools/
│   ├── archive_scoring_validator.py     # Scoring rules validator
│   ├── archive_bidding_validator.py      # Bidding rules validator
│   ├── archive_declaration_validator.py  # Declaration validator
│   └── run_rules_validation.py          # Master runner (all validators)
├── tests/
│   ├── test_scoring_validator.py        # Unit tests for scoring validator
│   └── test_bidding_validator.py        # Unit tests for bidding validator
└── docs/
    └── strategy_insights_report.md      # Highlight image analysis results
```

---

## 9. Success Criteria

### Must Achieve
1. **Card abnat validation**: `e1`/`e2` values match engine computation for ALL 1,095 rounds (>99% agreement)
2. **Round score validation**: `p1`/`p2` values match engine's `calculate_final_scores()` for >95% of rounds
3. **Kaboot detection**: `kbt` flag agrees with trick counting for 100% of rounds
4. **Cumulative score tracking**: `s1`/`s2` progression is consistent across all rounds in each game

### Should Achieve
5. **Declaration scoring**: `r1`/`r2` declaration lists match project detection
6. **Bidding statistics**: Comprehensive breakdown of bidding patterns across 109 games
7. **Khasara validation**: Identify all Khasara rounds and verify point transfer logic

### Nice to Have
8. **Full highlight image analysis** with strategic recommendations
9. **Discrepancy report**: If any rule differs from our implementation, document it precisely
10. **Test generation**: Create focused unit tests for any edge cases discovered

---

## 10. Quick Start Commands

```bash
# Run the scoring validator
python -m gbaloot.tools.run_rules_validation

# Run existing tests first (don't break them!)
cd c:\Users\MiEXCITE\Projects\baloot-ai
python -m pytest tests/game_logic/test_scoring_engine.py -v
python -m pytest tests/game_logic/test_scoring_comprehensive.py -v
python -m pytest tests/features/test_project_scoring.py -v

# Run new validator tests
python -m pytest gbaloot/tests/test_scoring_validator.py -v
python -m pytest gbaloot/tests/test_bidding_validator.py -v
```

---

## 11. Critical Constraints

1. **DO NOT modify the game engine files** unless you find a genuine bug (ask for approval first)
2. **DO NOT break existing tests** — run the full suite before and after
3. **The archive data is ground truth** — if our engine disagrees, investigate our engine
4. **Use existing parser/extractor code** — don't rebuild what's already working
5. **Player indexing**: Archives use 1-4 (1-indexed). Engine uses 0-3 (0-indexed). **Subtract 1.**
6. **Trump suit mapping**: Archive `ts={1:♠, 2:♣, 3:♦, 4:♥}` ≠ card_mapping.py `{0:♠, 1:♥, 2:♣, 3:♦}`
7. **Team mapping**: Team 1 = Players 1,3 (seats 0,2). Team 2 = Players 2,4 (seats 1,3).

---

## Appendix A: Point Value Quick Reference

### SUN Mode (No Trump)
| Rank | Points | Order (low→high) |
|------|--------|-------------------|
| 7 | 0 | 1st (weakest) |
| 8 | 0 | 2nd |
| 9 | 0 | 3rd |
| J | 2 | 4th |
| Q | 3 | 5th |
| K | 4 | 6th |
| 10 | 10 | 7th |
| A | 11 | 8th (strongest) |
**Per suit**: 30 abnat. **Total**: 4×30 = 120 + 10 bonus = **130 abnat → 26 GP**

### HOKUM Mode (Trump Suit)
| Rank | Side Suit Pts | Trump Pts | Side Order | Trump Order |
|------|--------------|-----------|------------|-------------|
| 7 | 0 | 0 | 1st | 1st |
| 8 | 0 | 0 | 2nd | 2nd |
| 9 | 0 | **14** | 3rd | **6th** |
| J | 2 | **20** | 4th | **8th (strongest)** |
| Q | 3 | 3 | 5th | 3rd |
| K | 4 | 4 | 6th | 4th |
| 10 | 10 | 10 | 7th | 5th |
| A | 11 | 11 | 8th | 7th |
**Trump suit**: 62 abnat. **Side suit**: 30 each. **Total**: 62 + 3×30 = 152 + 10 bonus = **162 abnat → 16 GP**

### Kaboot GP Values
| Mode | Normal Max GP | Kaboot GP |
|------|-------------|-----------|
| SUN | 26 | **44** |
| HOKUM | 16 | **25** |

---

## Appendix B: Team Structure in Archives

```
Team 1: Player 1 (seat 0) + Player 3 (seat 2) → "us"
Team 2: Player 2 (seat 1) + Player 4 (seat 3) → "them"
```

This matches our engine's team structure where Bottom(0)+Top(2) = "us" and Right(1)+Left(3) = "them".
