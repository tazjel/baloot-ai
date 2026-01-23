# Standard Rules Compliance & Rule Validation

This document outlines how we ensure our Baloot implementation follows professional standards and official rules.

## 1. Compliance Strategy

We use a three-pillared approach to rule validation:

### Pillar 1: Static Logic (Unit Tests)
We verify individual rule components in isolation to ensure mathematical and logical correctness.
- **Bidding**: Ashkal constraints, Doubling levels, Hokum/Sun variant selection.
- **Scoring**: Khasara logic, "Sun" point calculation (26 vs 16), Last trick bonus (+10).
- **Projects**: Sira, 50, 100, 400, and Baloot project declarations.

**Run Command:**
```bash
python scripts/verify_compliance.py
```

### Pillar 2: Situational Logic (Scenario Builder)
For complex edge cases (e.g., "What happens if Team A doubles, then Team B has 400 but loses the round?"), we use the **AI Studio Scenario Builder**.
- Allows manual input of specific hands for all 4 players.
- Enables step-by-step trick playback to verify engine state.
- Located in the **AI Studio** tab in the main application.

### Pillar 3: Behavioral Logic (The Scout)
We use batch game simulations to identify bot errors that might signal a rule misunderstanding.
- **Automated Scout**: Nightly runs that parse hundreds of games.
- **Gemini Analysis**: Uses LLMs to compare bot moves against "Optimal Play".

## 2. Key Rules Verified
- [x] **Ashkal**: Cannot be called if the floor card is an Ace.
- [x] **Sun Scored as 26**: Sun rounds are worth 26 points without projects.
- [x] **Khasara**: If the bidder team fails to get more than half the points, they get 0.
- [x] **Doubling (X2, X3, X4, Ghawa)**: Multipliers correctly applied to round totals.
- [x] **Sawa Claims**: Bot intelligently accepts/refuses claims using Master Card logic.
- [x] **Dealer Rotation**: Kawesh correctly rotates (Post-Bid) or redeals (Pre-Bid).

## 3. How to Report Discrepancies
If you find a rule that doesn't match standard rules:
1. Open the game in **AI Studio**.
2. Click **"Report Bad Move"**.
3. Tag the discrepancy as `Rule Mismatch`.
