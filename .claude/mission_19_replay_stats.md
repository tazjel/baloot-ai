# Mission 19: "The Historian" — Match Replay & Statistics

## Goal
Let players relive past games with visual replay and track their progress with stats and achievements.

## Deliverables

### 19.1 Visual Replay (enhance existing `useReplayNavigation.ts`)
- Render actual table with cards played in sequence (reuse Table component)
- Playback controls: Play/Pause, Speed (0.5x/1x/2x/4x), Skip trick/round, Jump to trick N
- Timeline scrubber with markers for key events (Kaboot, Baloot, Khasara, Double)
- Auto-generated commentary per trick ("Team A won with A♠, collecting 21 Abnat")
- AI analysis overlay: Toggle to compare bot recommendation vs actual play

### 19.2 Player Statistics (`frontend/src/services/StatsTracker.ts`)
- Persist match results to localStorage
- Dashboard: Win/Loss, win rate %, avg GP/round, Kaboot count, Galoss count, favorite bid, streak
- Per-difficulty stats (Easy/Medium/Hard/Khalid)
- Achievements: First Win, 10-Win Streak, Kaboot Master, Sun King, Hokum Hero, Galoss Survivor, etc.
- Session history: Last 50 matches with result, difficulty, notable events

### 19.3 Match Export
- Export to JSON (all tricks, bids, cards)
- Share replay link (encode match seed + decisions for deterministic replay)
- Screenshot mode (capture table state as image with scores)

## Key Constraint
- Stats stored in localStorage only (no server persistence needed for single-player)
- Replay uses existing match history data from `MatchHistoryRound[]` type
- Achievements are cosmetic only (no gameplay impact)
