---
description: Checklist for adding a new stateful engine or manager to the game.
---

# New Engine Checklist

When adding a new stateful engine/manager class to `game_engine/logic/`, follow these mandatory steps to prevent serialization bugs (like the Qayd freeze incident where engine state was lost across Redis round-trips).

## Steps

### 1. Create the Engine Class
- [ ] Create `game_engine/logic/<engine_name>.py`
- [ ] Engine should own a `state` dict (or Pydantic model)
- [ ] Add `reset()` method for round transitions

### 2. Register in `Game.__init__`
- [ ] Create the engine instance: `self.<engine> = NewEngine(self)`
- [ ] Alias state if needed: `self.<engine>_state = self.<engine>.state`

### 3. Serialize State in `Game.to_json()`
- [ ] Add `'<engine>_state': self.<engine>.state` to the `return {}` dict
- [ ] Ensure all values in the state dict are JSON-serializable (no Card objects, no enums — use `.value`)

### 4. Restore State in `Game.from_json()`
- [ ] Create the engine: `game.<engine> = NewEngine(game)`
- [ ] Restore saved state:
  ```python
  saved = data.get('<engine>_state')
  if saved and saved.get('active'):
      game.<engine>.state.update(saved)
  ```
- [ ] Alias: `game.<engine>_state = game.<engine>.state`

### 5. Expose to Frontend in `get_game_state()`
- [ ] Add the engine's frontend-facing state to the dict returned by `get_game_state()`
- [ ] Use a `get_frontend_state()` method if the state needs filtering

### 6. Route Actions in Frontend
- [ ] In `useGameSocket.ts`, ensure actions with your prefix are routed (convention: `action.startsWith('PREFIX')`)
- [ ] In `useActionDispatcher.ts`, exempt multi-step actions from `isSendingAction` guard if needed
- [ ] Add corresponding handlers in `server/handlers/game_actions.py`

### 7. Write Round-Trip Tests
// turbo
```bash
python -m pytest tests/game_logic/test_round_trip.py -v -k "NewEngine"
```

Add tests to `tests/game_logic/test_round_trip.py`:
- [ ] Inactive state survives round-trip
- [ ] Active state survives round-trip
- [ ] Each step/phase of the engine survives round-trip
- [ ] `get_frontend_state()` is consistent before/after round-trip

### 8. Write E2E Flow Test
- [ ] Add a test class in `tests/game_logic/test_<engine>_e2e_flow.py`
- [ ] Test the complete action pipeline with Redis round-trips between each step

## Quick Verification
// turbo
```bash
python -m pytest tests/game_logic/test_round_trip.py tests/game_logic/test_qayd_e2e_flow.py -v
```
