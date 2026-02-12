# Next Session Missions — Detailed Task Plans

> **Generated**: 2026-02-12 | **Recommended Order**: Mission 5 → 1 → 2 → 3 → 4

---

## Mission 1: "The Architect" — State Consolidation Refactor
> Eliminate the triple-ownership bug factory (~2 hours)

### Problem
Akka/Sawa state lives in 3 places: `GameState` (Pydantic), Manager objects (local dicts), and `StateBridge` (property aliases). This causes serialization bugs when layers go out of sync.

### Tasks

- [ ] **Phase 1: SawaState Migration** (simpler, do first)
  - [ ] In `trick_manager.py`: replace all `self.sawa_state[...]` dict access with `self.game.state.sawaState.field` attribute access
  - [ ] Replace `self.sawa_state.update({...})` with individual field assignments
  - [ ] Replace `self.sawa_state.clear()` with `self.game.state.sawaState = SawaState()`
  - [ ] Run tests: `python -m pytest tests/ -v --tb=short`

- [ ] **Phase 2: AkkaState Migration**
  - [ ] In `project_manager.py`: replace `self.akka_state[...]` with `self.game.state.akkaState.field`
  - [ ] Verify `AkkaState` Pydantic model has all fields used by ProjectManager
  - [ ] Run tests again

- [ ] **Phase 3: Cleanup**
  - [ ] In `game.py:to_json()` — remove manual akka/sawa serialization (Pydantic handles it)
  - [ ] In `game.py:from_json()` — remove manual akka/sawa restoration
  - [ ] Simplify `StateBridge` properties
  - [ ] Run full suite + E2E: `python scripts/verification/verify_game_flow.py`

### Key Files
| File | Change |
|------|--------|
| `game_engine/logic/trick_manager.py` | Dict→attribute access for sawa |
| `game_engine/logic/project_manager.py` | Dict→attribute access for akka |
| `game_engine/logic/game.py` | Remove manual sync in to_json/from_json |
| `game_engine/logic/state_bridge.py` | Simplify property aliases |
| `game_engine/core/state.py` | Verify Pydantic models have all fields |

### Verification
```bash
python -m pytest tests/ -v --tb=short    # 75 tests, 0 failures
python scripts/verification/run_serialization_guard.py  # 37 round-trip tests
python scripts/verification/verify_game_flow.py         # E2E with server
```

### Gotchas
- Never cache a local reference to `game.state.akkaState` — always go through `self.game.state`
- `sawa_state.update()` and `.clear()` don't work on Pydantic models
- After `reset_round()`, `sawaState = SawaState()` creates a NEW object — managers must re-read from `game.state`

---

## Mission 2: "The Polish" — Frontend UX Sprint
> Make the game feel alive and premium (~3 hours)

### Tasks

- [ ] **Card Play Animations**
  - [ ] Create `useCardAnimation.ts` hook with CSS keyframes for card throw/fly
  - [ ] In `GameArena.tsx`: animate cards entering `tableCards` area (scale + translate from player position to center)
  - [ ] Add trick-win sweep animation (winning cards slide to winner's side)

- [ ] **Round Results Enhancement**
  - [ ] Redesign `RoundResultsModal.tsx` with animated score counter
  - [ ] Add team color bars showing point breakdown (tricks + bonuses)
  - [ ] Add a "winner crown" animation for the winning team

- [ ] **Sound Design**
  - [ ] Create `sounds/` directory with: card-play, trick-win, bid-place, project-declare, game-over
  - [ ] Build `useSoundEffects.ts` hook with volume control
  - [ ] Integrate with existing `useGameAudio` or replace it
  - [ ] Add sounds to: card play, trick resolution, bidding, Sawa/Akka events

- [ ] **Mobile Responsive Pass**
  - [ ] Audit `Table.tsx` / `GameArena.tsx` at 375px and 768px widths
  - [ ] Fix card sizing, player avatar positions, HUD overflow
  - [ ] Make ActionBar scrollable or collapsible on small screens
  - [ ] Test via Playwright at mobile viewport sizes

### Key Files
| File | Change |
|------|--------|
| `frontend/src/hooks/useCardAnimation.ts` | NEW — card animation logic |
| `frontend/src/hooks/useSoundEffects.ts` | NEW — sound effect system |
| `frontend/src/components/table/GameArena.tsx` | Card play animations |
| `frontend/src/components/RoundResultsModal.tsx` | Score animation redesign |
| `frontend/src/index.css` | Animation keyframes, responsive breakpoints |

### Verification
- Visual: Playwright screenshots at key moments (card play, trick win, round end)
- Mobile: Playwright screenshots at 375px and 768px widths
- Performance: No jank during animations (check with browser DevTools)

---

## Mission 3: "The Strategist" — Smarter Bot AI
> Make bots play like experienced Baloot players (~3 hours)

### Tasks

- [ ] **Partner Signaling**
  - [ ] In `bot_strategy.py`: when leading, prefer strong suits to signal partner
  - [ ] Track what suits partner has played/avoided → infer their hand
  - [ ] When partner leads, support their suit if possible

- [ ] **Defensive Play**
  - [ ] If opponents bid and won the contract, play defensively (cut trumps early)
  - [ ] When playing last in a trick, save high cards if partner is already winning
  - [ ] Lead short suits to create void for future trumping

- [ ] **Score-Aware Decisions**
  - [ ] Near game end (score > 120), increase aggression in bidding
  - [ ] When behind, take riskier bids; when ahead, play conservatively
  - [ ] Factor in project bonus points when deciding to declare

- [ ] **Project-Aware Play**
  - [ ] Protect cards that are part of declared projects
  - [ ] Target opponent project cards when able
  - [ ] Factor project point value into bid evaluation

- [ ] **Improved Sawa Timing**
  - [ ] Calculate exact remaining tricks needed vs. cards in hand
  - [ ] Claim Sawa only when 100% certain (analyze remaining cards)
  - [ ] Consider opponent's possible remaining cards before claiming

### Key Files
| File | Change |
|------|--------|
| `game_engine/logic/bot_strategy.py` | Core strategy improvements |
| `game_engine/logic/heuristic_bidding.py` | Score-aware and project-aware bidding |
| `game_engine/logic/trick_manager.py` | Helper methods for card tracking |

### Verification
```bash
# Use Scout Automation skill for batch testing
python scripts/scout/run_scout.py --games 100 --strategy advanced
# Compare win rates: old strategy vs new
python scripts/scout/compare_strategies.py
# Unit tests
python -m pytest tests/features/test_bot_strategy.py -v
```

---

## Mission 4: "The Multiplayer" — Online Play Polish
> Make online mode production-ready (~4 hours)

### Tasks

- [ ] **Room Browser**
  - [ ] Backend: Add `/api/rooms` endpoint listing open rooms with player counts
  - [ ] Frontend: Create `RoomBrowser.tsx` component with room list, join buttons
  - [ ] Add auto-refresh every 5 seconds via polling or socket events
  - [ ] Filter: show only rooms waiting for players

- [ ] **Reconnection Handling**
  - [ ] Backend: On disconnect, mark player as `disconnected` (not removed) for 60 seconds
  - [ ] Backend: On reconnect with same session, restore player to their seat
  - [ ] Frontend: Show "Reconnecting..." overlay with spinner
  - [ ] If player doesn't return in 60s, replace with bot

- [ ] **Spectator Mode**
  - [ ] Backend: Allow joining a room as `spectator` role (read-only)
  - [ ] Frontend: Hide ActionBar, hand, and interactive elements for spectators
  - [ ] Show spectator count badge on table
  - [ ] Spectators see all 4 hands revealed

- [ ] **In-Game Emotes**
  - [ ] Expand `EmoteMenu.tsx` with Baloot-specific emotes (👏 يا حظك, 😤 حرام, 🔥 ماشاء الله)
  - [ ] Backend: Broadcast emotes via socket to all players in room
  - [ ] Frontend: Show floating emote animation near sender's avatar
  - [ ] Rate-limit to 1 emote per 3 seconds

### Key Files
| File | Change |
|------|--------|
| `frontend/src/components/RoomBrowser.tsx` | NEW — room listing UI |
| `frontend/src/components/EmoteMenu.tsx` | Expand emote system |
| `server/socket_handler.py` | Reconnection logic, spectator events |
| `server/controllers.py` | Room listing API |
| `server/room_manager.py` | Disconnect timeout, spectator roles |

### Verification
- Open 2 browser tabs → create room in tab 1, join from tab 2
- Disconnect tab 2 → verify reconnection within 60 seconds
- Open tab 3 as spectator → verify read-only view
- Test emote broadcasting between tabs

---

## Mission 5: "The Cleaner" — Code Hygiene Sprint ✅ COMPLETE
> Completed 2026-02-12

### Tasks

- [x] **Remove Debug Logs** — No debug console.logs found (already cleaned)
- [x] **Schema Audit** — `test_schema_completeness.py` exists and passes
- [x] **TypeScript Strictness** — `tsc --noEmit` → 0 errors, no `as any` casts
- [x] **Dead Code Cleanup** — Zero references to removed features (AI Studio, Replay, Academy, Visionary)
- [x] **Documentation Refresh** — `CODEBASE_MAP.md` updated with decomposed files + expanded hooks/utils
