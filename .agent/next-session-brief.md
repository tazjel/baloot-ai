# Next Session: Consolidate State Ownership (Architectural Refactor)

## The Problem

Akka and Sawa state currently exists in **three places simultaneously**, which is the root cause of repeated serialization bugs:

```
1. GameState (Pydantic model)    → game.state.akkaState / game.state.sawaState
2. Manager objects               → ProjectManager.akka_state / TrickManager.sawa_state
3. Game class (via StateBridge)   → game.akka_state / game.sawa_state (property aliases)
```

The bridge (layer 3) syncs layers 1↔3, but **layer 2 (managers) maintains its own copy**. When a manager updates its local dict, the Pydantic model doesn't know. The `to_json`/`from_json` methods must then manually shuttle data between all three — and every new feature risks forgetting a layer.

## The Goal

Make managers read/write directly from `game.state.akkaState` and `game.state.sawaState` instead of maintaining their own copies. This eliminates the manual sync in `to_json`/`from_json`.

## Key Files to Modify

### 1. `game_engine/logic/project_manager.py` (Akka)
- **Line ~15**: `self.akka_state = {...}` initializes a LOCAL dict
- **Lines throughout**: reads/writes `self.akka_state`
- **Goal**: Replace `self.akka_state` with `self.game.state.akkaState` (a Pydantic `AkkaState` model)
- **Watch out**: `AkkaState` is a Pydantic model (not a plain dict). You'll need to use attribute access (`state.akkaState.active`) not dict access (`state['active']`).

### 2. `game_engine/logic/trick_manager.py` (Sawa)
- **Line ~10**: `self.sawa_state = {...}` initializes a LOCAL dict
- **Lines 165-282**: `handle_sawa()` reads/writes `self.sawa_state` extensively
- **Goal**: Replace `self.sawa_state` with `self.game.state.sawaState`
- **SawaState** is also a Pydantic model.

### 3. `game_engine/core/state.py` (Pydantic models)  
- **`AkkaState`** (around line 80-90): Has fields like `active`, `claimer`, `claimerIndex`, `suits`, `timestamp`
- **`SawaState`** (around line 60-75): Has fields like `active`, `claimer`, `claimer_index`, `status`, `valid`, `challenge_active`, `cards_left`
- **Check these model definitions** match all the fields that ProjectManager and TrickManager currently use. If a field is missing from the Pydantic model, add it.

### 4. `game_engine/logic/state_bridge.py` (Property aliases)
- **Lines 206-296**: Contains `@property` aliases like `game.akka_state` and `game.sawa_state`
- After the refactor, these can be simplified to just return `self.state.akkaState` / `self.state.sawaState` directly (they may already do this — verify)

### 5. `game_engine/logic/game.py` (Serialization)
- **`to_json()` (~line 489)**: Currently manually adds `akka_state` and `sawa_state` to the JSON output
- **`from_json()` (~line 565-588)**: Currently manually restores these states
- **After refactor**: These lines become UNNECESSARY because `state.model_dump()` already serializes `akkaState`/`sawaState` automatically. You can delete them.

## Gotchas & Risks

1. **Dict vs Pydantic model**: TrickManager does `self.sawa_state.update({...})` and `self.sawa_state.clear()` — these won't work on a Pydantic model. Replace with attribute assignment: `self.game.state.sawaState.active = True` etc.

2. **`sawa_state['status']` dict access**: Many places use dict-style access. Must change to attribute access.

3. **`reset_round()` in GameState** (line ~195): Already resets `sawaState = SawaState()` and `akkaState = AkkaState()`. Verify managers don't hold stale references after reset.

4. **Reference identity**: Currently `game.akka_state` is the same Python dict object as `project_manager.akka_state`. After refactor, if you change the Pydantic model to a new instance (e.g., `state.akkaState = AkkaState()`), the manager's reference breaks. The manager must always go through `self.game.state.akkaState`, never cache a local reference.

5. **Qayd state** (`qayd_engine.state`): Has the same triple-ownership pattern but is already working. Consider consolidating it too, or leave for a separate PR.

## Testing Strategy

1. **Run existing round-trip tests FIRST**: `python scripts/verification/run_serialization_guard.py` (37 tests, <1s). These MUST still pass.
2. **Run full test suite**: `python -m pytest tests/game_logic/ -v --tb=short` (75 tests). Zero regressions.
3. **Run E2E verification**: `python scripts/verification/verify_game_flow.py` with the server running (`python server/main.py`).
4. **Key tests to watch**:
   - `TestAkkaRoundTrip` (4 tests) — validates Akka survives serialization
   - `TestSawaRoundTrip` (4 tests) — validates Sawa survives serialization
   - `test_sawa_flow` in test_game_logic.py — validates live Sawa claim

## Suggested Order of Operations

1. Start with **SawaState** (simpler, fewer fields)
2. Make TrickManager use `self.game.state.sawaState` everywhere
3. Run tests → fix breakages
4. Then do **AkkaState** in ProjectManager
5. Run tests again
6. Clean up `to_json`/`from_json` — remove manual akka/sawa serialization
7. Run full suite + E2E
8. Optionally simplify StateBridge properties

## Current Test Baseline

```
75 passed, 0 failed, 8 warnings
```

Any regression from this number means the refactor broke something.
