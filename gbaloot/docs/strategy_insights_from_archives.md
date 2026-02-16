# Strategy Insights from 109 Kammelna Archive Games

**Generated from**: 109 games, 1,629 rounds (1,095 played + 534 waraq)
**Data source**: Mobile Kammelna archives (real human player games)

---

## 1. Mode Distribution & Bidding Phase

| Metric | Value |
|--------|-------|
| HOKUM rounds | 586 (52.9% of played) |
| SUN rounds | 375 (33.9% of played) |
| Ashkal rounds | 142 (12.8% of played) |
| Waraq (re-deal) | 506 (31.4% of all rounds) |

**Key insight**: Almost 1 in 3 rounds is a waraq (re-deal). This means hands are frequently weak enough that nobody wants to bid. The bot should be cautious about bidding marginal hands.

### Round 1 vs Round 2 Resolution

| Phase | HOKUM | SUN | Ashkal | Total |
|-------|-------|-----|--------|-------|
| R1 resolved | 391 | 259 | 75 | 725 |
| R2 resolved | 195 | 258 | 67 | 520 |

**Key insight**: HOKUM is 2:1 R1 vs R2 (players bid HOKUM aggressively when they see a good floor card). SUN is almost 1:1 — players often wait for R2 to bid SUN, perhaps to see what opponents pass on first.

### Turn-to-SUN Switches
- 71 rounds (6.4% of played) involved a player bidding HOKUM in R2 then switching to SUN
- This is a significant strategic pattern — players use HOKUM as a "placeholder" bid in R2 then reassess

---

## 2. Bidder Position Analysis

| Position from Dealer | Count | % |
|---------------------|-------|---|
| Position 1 (first to bid) | 321 | 29.0% |
| Position 2 | 265 | 23.9% |
| Position 3 | 303 | 27.4% |
| Position 4 (dealer) | 214 | 19.3% |

**Average bidder position**: 2.37 (skews early)

**Key insight**: The first bidder (right of dealer) wins the contract most often — first-mover advantage is real. The dealer (position 4) bids least often, likely because by position 4, someone has usually already bid. Position 3 is surprisingly active (27.4%) — this may indicate partner-aware bidding (position 3 is the partner of position 1).

**Bot recommendation**: Be more aggressive in position 1 (first to bid), slightly less aggressive in position 4 (dealer).

---

## 3. Khasara (Bidder Penalty) Analysis

| Mode | Khasara Rate | Total Rounds |
|------|-------------|-------------|
| SUN | 28.5% (147/515) | 515 |
| HOKUM | 15.9% (92/580) | 580 |
| **Overall** | **21.8% (239/1095)** | **1095** |

**Key insight**: SUN khasara rate is nearly DOUBLE that of HOKUM. This makes sense — in SUN mode, all suits score equally, making it harder to control. In HOKUM, the trump suit gives the bidder a natural advantage.

**Bot recommendation**:
- Require higher hand strength for SUN bids (compensate for 28.5% penalty rate)
- HOKUM bids are safer — the trump advantage works. Current threshold may be too conservative.

---

## 4. Kaboot (Clean Sweep) Analysis

| Mode | Kaboot Rate | Base GP |
|------|------------|---------|
| SUN | 13.8% (71/515) | 44 GP |
| HOKUM | 9.3% (54/580) | 25 GP |
| **Overall** | **11.4% (125/1095)** | |

**Key insight**: Kaboot happens in ~1 in 9 rounds overall. SUN kaboot is more common than HOKUM kaboot (13.8% vs 9.3%), likely because strong SUN hands can dominate all suits.

**Bot recommendation**:
- The kaboot_pursuit module should be more aggressive in SUN mode
- At ~14% base rate in SUN, kaboot is a realistic strategic goal (not just a lucky outcome)
- The 44 GP SUN kaboot base is massive — worth pursuing even at moderate risk

---

## 5. Doubling (Radda) Analysis

| Level | Count | % of Played |
|-------|-------|-------------|
| Normal (×1) | 1062 | 95.9% |
| Double (×2) | 31 | 2.8% |
| Triple (×3) | 2 | 0.2% |
| Four (×4) | 3 | 0.3% |
| Gahwa (max) | 9 | 0.8% |

**HOKUM variants when doubled**: 33 closed, 2 open (94% closed)

**Key insight**: Doubling is rare (4.1% of rounds) but overwhelmingly uses the "closed" HOKUM variant. When defenders double, they almost always choose closed (trump face-down) — this significantly handicaps the bidder.

**Bot recommendation**:
- Doubling decision should be conservative (only 4.1% of real games use it)
- When doubling HOKUM, always prefer closed variant (as humans do 94% of the time)
- Qahwa (max escalation) happens in 0.8% of games — reserve for extremely strong defensive hands

---

## 6. GP Distribution

| Metric | SUN | HOKUM |
|--------|-----|-------|
| Avg GP per team per round | 17.3 | 11.5 |
| GP target (full deck) | 26 | 16 |
| Common winning GP | ~18-22 | ~10-13 |

**Key insight**: Average GP is well below the maximum (17.3/26 for SUN, 11.5/16 for HOKUM), meaning points are usually split somewhat evenly. The bidder advantage is real but not overwhelming.

---

## 7. Before-You Counter-Bids

- 27 rounds (2.4%) involved a "before-you" SUN counter-bid
- This is the mechanism where another player steals a SUN bid by claiming priority

**Bot recommendation**: The before-you mechanism is rare but strategically important. The bot should consider counter-bidding SUN when holding a very strong hand and the original SUN bidder is an opponent.

---

## 8. Scoring Rules Confirmed

From the scoring validator (98.8% card abnat agreement, 87.5% GP agreement, 100% kaboot):

### GP Conversion (Confirmed)
- **SUN**: `floor(card_abnat / 5)` — strict floor division
- **HOKUM**: Asymmetric rounding at `card_abnat / 10` — 0.5 stays down, >0.5 rounds up
- **Projects SUN**: `(declaration_value × 2) // 10`
- **Projects HOKUM**: `declaration_value // 10`
- **Tiebreak**: Remainder goes to BIDDER team

### Scoring Pipeline Order (Confirmed)
1. Convert card abnat to GP
2. Add tiebreak to bidder
3. Add project GP (from declarations)
4. Check khasara: if bidder_gp ≤ opponent_gp → all to opponent
5. Apply em multiplier (×2, ×3, ×4 or flat 152 for gahwa)
6. Add baloot GP (immune to all multipliers)

### Kaboot Formula (100% Confirmed)
- Winner gets: `base_gp + all_project_gp(both teams) + all_baloot_gp`
- Base: 44 (SUN), 25 (HOKUM)

---

## 9. Actionable Recommendations for Bot AI

### Bidding Module (`bidding.py`)
1. **Increase SUN threshold** — 28.5% khasara rate means SUN bids are risky
2. **Decrease HOKUM threshold slightly** — 15.9% khasara rate suggests HOKUM is safer
3. **Add position awareness** — be more aggressive in position 1 (29% win rate)
4. **Model waraq probability** — 31.4% of rounds are re-deals; don't fear passing

### Kaboot Pursuit (`kaboot_pursuit.py`)
1. **Higher base activation in SUN** — 13.8% base rate makes pursuit viable
2. **Track opponent points** — kaboot requires 0 opponent card points
3. **Integrate with project GP** — kaboot total includes ALL declarations

### Defense Strategy (`defense_plan.py`)
1. **Closed HOKUM doubling** — when doubling, always choose closed (94% human preference)
2. **Khasara exploitation** — target 50%+ of card GP to trigger bidder penalty
3. **Point splitting** — in SUN, even modest defense creates khasara risk

### Radda/Doubling Module
1. **Conservative doubling** — only 4.1% of real games use it
2. **Doubling = high confidence** — humans only double when very sure of defense
3. **Gahwa as ultimate weapon** — rare (0.8%) but devastating (flat 152 GP)
