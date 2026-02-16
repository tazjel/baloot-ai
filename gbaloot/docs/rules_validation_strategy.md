# Rules Validation Strategy — Answers to 19 Pre-Build Questions

> Generated: 2026-02-16

---

## Data Intelligence

### Q1. Data Inventory — All Event Types

Surveyed 5 diverse archives (sessions 10, 265, 4977, 7704, 3133). **12 unique event types** found:

| `e` | Name | Key Fields |
|-----|------|-----------|
| 1 | Round start | `fc` (first card), `t1s`/`t2s` (team scores at round start) |
| 2 | Bid | `b`, `gm`, `ts`, `rb`, `gem`, `rd`, `hc` |
| 3 | Declaration | `prj` (type) or `prjC` (card bitmask confirmation) |
| 4 | Card play | `c` (card index 0-51) |
| 5 | Kaboot/surrender | No extra fields |
| 6 | Trick boundary | `p` (animation target, NOT reliable winner) |
| 7 | Qayd challenge | `ch`, `wc`, `ac`, `cihs`, `ets` |
| 8 | Chat | `uid`, `msg` |
| 10 | Disconnect | `dbId` |
| 11 | Reconnect | `dbId`, `n`, `rp`, `s` |
| 12 | Round result | Full scoring object (see Q6) |
| 15 | Hand dealt | `bhr`, `fhr` (card bitmasks) |

No undocumented event types found beyond these 12.

### Q2. e=12 Completeness

**NO — not every round has e=12.** Rounds ending in `waraq` (all 4 players pass both bidding rounds) have NO e=12 because no game is played. Found 13+ waraq rounds across 5 sample files.

**Handling**: Skip waraq rounds silently for scoring validation (nothing to validate). Count them for bidding statistics (they represent all-pass redeals).

### Q3. e1/e2 Semantics — Last-Trick Bonus

**CONFIRMED: e1 + e2 INCLUDES the 10-point last-trick bonus.**

Proof across 20+ rounds:
- HOKUM: e1 + e2 = **152** (every single round, including kaboot)
- SUN: e1 + e2 = **120** (every single round, including kaboot)

HOKUM card totals: 142 (card points) + 10 (last trick) = 152.
SUN card totals: 110 (card points) + 10 (last trick) = 120.

**Wait — SUN should be 120 card points + 10 = 130?** No: SUN = 4 suits * 30 = 120 card points. The convention in the mission spec says 130 total with last trick. But the data shows e1+e2 = 120 for SUN. This means either:
- SUN base is 110 + 10 = 120, OR
- e1/e2 do NOT include last trick for SUN either, and the base is 120.

Actually: SUN card values per suit = A(11)+10(10)+K(4)+Q(3)+J(2) = 30. 4 suits = 120. WITHOUT last trick bonus, e1+e2 = 120. So **e1/e2 = raw card points WITHOUT last-trick bonus for SUN**.

For HOKUM: Trump(62) + 3*Side(30) = 62+90 = 152. Without last trick = 142. But e1+e2 = 152. So HOKUM DOES include last trick?

Wait, recalculate HOKUM side suits: A(11)+10(10)+K(4)+Q(3)+J(2)+9(0)+8(0)+7(0) = 30. Trump: J(20)+9(14)+A(11)+10(10)+K(4)+Q(3) = 62. Total = 62 + 3*30 = 152. That's ALREADY 152 without any last-trick bonus!

**REVISED ANSWER**: e1+e2 = 152 (HOKUM) = total card points in the deck = 152. e1+e2 = 120 (SUN) = total card points in the deck = 120. **NEITHER includes the last-trick bonus.** The last-trick bonus is added separately in p1/p2.

This is consistent with p = e + declarations + 10_for_last_trick_winner.

### Q4. p1/p2 and s1/s2 Semantics

**Proven with arithmetic from 5+ rounds:**

- **e1/e2** = Raw card points earned by each team (NO last-trick bonus, NO declarations). e1+e2 = 152 (HOKUM) or 120 (SUN).
- **p1/p2** = Total Abnat = e + declarations + 10 (if last-trick winner). The last-trick winner's team gets +10 added to their p value.
- **s1/s2** = **Per-round Game Points (GP)**, NOT cumulative. Header-level s1/s2 = sum of all per-round s values.

Proof: Session 10 R1 (HOKUM): e1=47, e2=105 (sum=152). r2=[sira:20]. lmw=2. p1=47=e1 (no decl, not last winner). p2=135=105+20+10 (e2+sira+last). s1=5 (GP). s2=13 (GP). Sum across all rounds: s1_total=49=header_s1. s2_total=184=header_s2.

### Q5. Declaration Data — prjC Presence

**NO — prjC is NOT always present.** Two types of e=3 events:
1. `{prj: N}` — announcement only (always present for declarations)
2. `{prjC: bitmask}` — card confirmation (appears later, not always)

For scoring validation, we only need the `r1`/`r2` arrays in e=12 which have the definitive declaration list with names and values. We do NOT need to decode prjC.

### Q6. All Fields in e=12.rs

| Field | Type | Description | Always present? |
|-------|------|-------------|----------------|
| p1 | int | Team 1 Abnat | Only if team 1 scored (absent in kaboot losses) |
| p2 | int | Team 2 Abnat | Only if team 2 scored |
| lmw | int | Last-move winner team (1 or 2) | YES |
| m | int | Mode (1=SUN, 2=HOKUM) | YES |
| r1 | array | Team 1 declarations [{n, val}] | YES (can be []) |
| r2 | array | Team 2 declarations [{n, val}] | YES (can be []) |
| e1 | int | Team 1 raw card points | Only if earned |
| e2 | int | Team 2 raw card points | Only if earned |
| w | int | Round winner (1 or 2) | YES |
| s1 | int | Team 1 GP this round | Only if team 1 earned GP |
| s2 | int | Team 2 GP this round | Only if team 2 earned GP |
| b | int | Bidder team (1 or 2) | YES |
| kbt | int | Kaboot flag (1=kaboot) | Only when kaboot |
| em | int | Escalation multiplier (2/3/4) | Only when > 1 |
| lr | int | Last round flag | Only on game-ending round |
| lmw | int | Last match winner | Present |
| cc | int | Challenge confirmed (1=qayd applied) | Only when qayd |

Declaration names in r1/r2: "sira"(=20), "baloot"(=20), "50"(=50), "100"(=100), "400"(=400).

---

## Architecture Decisions

### Q7. One Validator or Three?

**Decision: One unified validator with modular internals.**

Arguments for unified:
- All data comes from the same file/round, parsed once
- Scoring depends on bidding (mode, trump, multiplier) and declarations (project GP)
- A single pass avoids redundant parsing
- Better testability of the FULL pipeline

Arguments for separate:
- Each category (scoring, bidding, declarations) has independent validation logic
- Easier to debug divergences in one area

**HYBRID approach**: One `archive_rules_validator.py` that does a single pass per round, with internal methods for each validation category. This avoids three separate files that all parse the same data.

### Q8. Engine Coupling vs Independence

**Decision: HYBRID approach.**

- **Card abnat**: Independent implementation (sum card point values from constants — simple, 10 lines). This gives TRUE independent validation.
- **GP conversion**: Independent implementation (rounding formula — also simple).
- **Kaboot/Khasara/Doubling**: Independent (just conditionals).
- **Declaration scoring**: Use r1/r2 from archive directly (no need to reimport engine).

We do NOT call `ScoringEngine` or `GameComparator`. We implement the math independently from `constants.py` values. This catches engine bugs the coupled approach would miss.

### Q9. Quick Win Triage

| Validation | Effort | Confidence Gained | Priority |
|-----------|--------|-------------------|----------|
| Card abnat (e1/e2 vs computed) | ~20 lines | HIGH — validates trick point calculation | 1st |
| Kaboot detection (kbt vs trick count) | ~5 lines | HIGH — simple flag check | 1st |
| Cumulative score tracking (s1/s2) | ~10 lines | HIGH — validates GP math end-to-end | 2nd |
| Declaration scoring (r1/r2 matching) | ~15 lines | MEDIUM — validates project system | 2nd |
| Khasara detection | ~10 lines | MEDIUM | 3rd |
| Doubling multiplier (em application) | ~10 lines | MEDIUM | 3rd |
| Bidding statistics (no validation, just counting) | ~30 lines | LOW (insight, not validation) | 4th |

**80/20**: Card abnat + kaboot + cumulative scores = 35 lines for 80% confidence.

### Q10. Existing Code Reuse

- `archive_parser.py`: Reuse `parse_archive()` and `load_all_archives()` for file loading
- `archive_trick_extractor.py`: Reuse `_compute_winner()` for team attribution per trick, reuse `_resolve_trump()` for trump determination
- `constants.py`: Import `POINT_VALUES_SUN`, `POINT_VALUES_HOKUM` for card abnat computation
- `card_mapping.py`: Reuse `index_to_card()` for card conversion

**Do NOT extend archive_trick_extractor.py** — keep it focused on tricks. Create a new validator module.

---

## Validation Strategy

### Q11. Ground Truth Hierarchy

**Internal consistency checks to detect source platform bugs:**
1. `e1 + e2` must equal 152 (HOKUM) or 120 (SUN) — if not, archive is corrupt
2. `s` values across all rounds must sum to header `s1`/`s2` — if not, accumulation bug
3. `p = e + declarations + last_trick_bonus` must hold — if not, archive p formula differs
4. Kaboot rounds must have one team winning all 8 tricks

If the archive fails internal consistency, it's a source platform bug (category D). If it's consistent but disagrees with our engine, investigate our engine (category C).

### Q12. Statistical vs Exhaustive

**EXHAUSTIVE. Validate ALL 1,095 rounds.**

Reasons:
- We already have the infrastructure from the trick benchmark (it processes all 109 files in seconds)
- Edge cases (kaboot, doubled, declarations) are rare — sampling might miss them
- Exhaustive gives absolute confidence
- The code is the same whether we validate 50 or 1,095 rounds

### Q13. Divergence Response Plan

Priority order for triage:
1. **Check internal consistency** first — if e1+e2 != expected, it's our parsing (A) or source platform (D)
2. **Check our card abnat computation** — if we compute wrong trick points, it's a mapping bug (B) or our point table is wrong
3. **Compare GP conversion** — if abnat matches but GP doesn't, it's a rounding rule difference (C)
4. **Pattern analysis** — cluster divergences by game_mode, multiplier level, kaboot status to identify systemic issues

### Q14. Edge Case Hunting

Found in archives:
- **Kaboot rounds**: YES — 8+ found (sessions 10, 265, 4977, 3133, 7704)
- **Doubled/tripled rounds**: YES — session 10 R8 has em=3 (tripled)
- **Rounds with both declarations**: YES — session 4977 R8 (team 1: 50, team 2: baloot)
- **Rounds with Baloot + declarations**: YES — session 10 R5 (sira+sira+baloot)
- **Qayd challenge**: YES — session 7704 R8 (cc=1)
- **Gahwa rounds**: Need to search for em >= 100 across all archives
- **GP rounding tiebreak**: Will surface during validation

---

## Highlight Images

### Q15. Image Value Assessment

**ZERO statistical value.** All 9 highlight images are decorative achievement badge icons (Arabic text + card illustrations):
- bidStrength = "قوة المشترى" (Buyer's Strength) badge
- kaboot = "المكبت" (The Kaboot) badge
- lostBid = "النكبة" (The Disaster) badge
- etc.

No charts, no numbers, no data to extract.

### Q16. Raw Data vs Screenshots

**Raw data is infinitely more valuable.** We can compute exact statistics from 109 archives: bidding rates, kaboot frequency, khasara rate, declaration distribution, doubling chain depth — all with precise numbers. The images are just stickers.

**Decision: SKIP image analysis entirely. Compute statistics from raw data instead.**

---

## Execution Plan

### Q17. Proposed Execution Order

1. **Build unified scoring/rules validator** (~1 hour)
   - Card abnat validation (e1/e2 vs engine-computed)
   - p1/p2 validation (e + declarations + last_trick)
   - Kaboot detection (kbt flag vs trick count)
   - Khasara detection (bidder_team vs winner)
   - GP conversion (s1/s2 vs computed GP from p1/p2)
   - Cumulative score tracking (sum of s values vs header s1/s2)
   - Doubling multiplier validation (em field)

2. **Build bidding statistics extractor** (~30 min)
   - Mode distribution (SUN vs HOKUM)
   - All-pass (waraq) rate
   - Doubling chain depth distribution
   - OPEN vs CLOSED variant distribution
   - Round 1 vs Round 2 resolution rate

3. **Run against all 109 archives** (~5 min)
   - Generate comprehensive report
   - Investigate any divergences

4. **Write tests** (~30 min)
   - Unit tests for each validation function
   - Integration tests with sample archive data

5. **Save strategy insights report** (~15 min)
   - Statistics from raw data (replaces image analysis)

### Q18. Definition of Done

| Category | Proof of Validation |
|----------|-------------------|
| Card abnat | e1/e2 match computed values for all 1,095 rounds, 0 divergences |
| Kaboot | kbt flag matches trick-count for 100% of rounds |
| Cumulative scores | Sum of per-round s values = header s1/s2 for all 109 games |
| Declarations | r1/r2 names and values match expected types |
| Khasara | All rounds where bidder lost correctly identified |
| GP conversion | s1/s2 match computed GP for >95% of rounds |
| Bidding stats | JSON report with mode/doubling/variant distributions |

### Q19. Failure Mode

**Complete the full run first, then analyze patterns.** If >5% diverge:
1. Cluster divergences by: game_mode, em (multiplier), kbt (kaboot), presence of declarations
2. If clustered in one category (e.g., all doubled rounds), investigate that formula
3. If scattered, likely a parsing issue — check a sample manually
4. Document ALL divergences with enough context to debug later

---

## Key Correction to Mission Spec

The mission spec states several things that need verification:
1. **"e1/e2 include last-trick bonus or not?"** — They do NOT. e1+e2 = 152 (HOKUM) or 120 (SUN) = deck total WITHOUT last trick bonus. The +10 is added in p1/p2.
2. **"s1/s2 cumulative?"** — They are NOT cumulative. They are per-round GP. Header s1/s2 is the cumulative total.
3. **Highlight images** — Not statistical charts. Just badges. Skip them.
