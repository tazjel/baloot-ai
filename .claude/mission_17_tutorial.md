# Mission 17: "The Teacher" — Interactive Tutorial & Learning Mode

## Goal
Onboard new players with a guided tutorial, provide learning hints during play, and offer a practice mode.

## Deliverables

### 17.1 Guided Tutorial (`frontend/src/components/Tutorial.tsx`)
7-lesson overlay system:
1. **Card Basics**: 32 cards, SUN vs HOKUM rank orders, point values. Quiz: "Which is worth more?"
2. **Bidding**: Walk through a sample round. Explain Pass/Hokum/Sun/Ashkal
3. **Trick Play**: Play 3 guided tricks with highlights on legal cards
4. **Scoring**: Abnat, GP, Khasara, Kaboot breakdown
5. **Projects**: Sira, 50, 100, 400 — hierarchy and blocking rules
6. **Special Rules**: Baloot, Kawesh, Ashkal, Doubling, Sawa, Galoss
7. **First Game**: Play a full match with hints enabled against Easy bots

### 17.2 Hint System (`frontend/src/hooks/useHintSystem.ts`)
- New socket event: `request_hint` → server runs bot AI on player's hand → returns top-3 cards + reasons
- Bid hints: "Strong in ♠ (J+9+A). Consider Hokum ♠" with confidence meter
- Play hints: Card glow on recommended play + tooltip explanation
- Post-trick analysis: "Q♥ would have won" (shown after trick if enabled)
- Toggle in Settings > "Show Hints" (default OFF)

### 17.3 Practice Mode
- Predefined scenario deals (strong trump, defensive, Kaboot opportunity, Galoss danger)
- Undo/redo last play
- Card reveal toggle (see all 4 hands)
- Speed controls (pause after trick, slow bots, fast-forward)

## Key Constraint
- Hint API reuses existing bot AI — no new strategy code needed
- Tutorial state persists in localStorage (resume where you left off)
- Practice mode is single-player only (no multiplayer complications)
