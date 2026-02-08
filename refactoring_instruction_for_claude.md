# Lean Refactoring Mission: Deconstruct PlayingStrategy

## Core Objective
Efficiently split the monolithic `PlayingStrategy` (1000+ lines) into composable components using a **Lift & Shift** approach.
**Constraint**: Move logic *as-is* to preserve behavior. Do not rewrite algorithms yet. Minimize token usage by focusing strictly on structural refactoring.

## 1. Target Architecture
Implement the following file structure. Do not "propose" it, just **build it**.

### A. Component Files
1.  `ai_worker/strategies/components/base.py`:
    - Abstract base class `StrategyComponent`.
    - Interface: `get_decision(ctx: BotContext) -> dict | None`.
2.  `ai_worker/strategies/components/sun.py`:
    - logic from `_get_sun_lead` and `_get_sun_follow`.
    - logic from Heuristics helpers (`_find_best_winner_sun`, etc).
3.  `ai_worker/strategies/components/hokum.py`:
    - logic from `_get_hokum_lead` (fix indentation here!) and `_get_hokum_follow`.
    - logic from Heuristics helpers.
4.  `ai_worker/strategies/components/projects.py`:
    - logic from `_check_sawa` and `_check_akka`.
    - logic from `_calculate_projects`.

## 2. Execution Steps (Token Optimized)

### Step 1: Create Components
Create the new files and copy the relevant methods into them. Ensure `BotContext` is imported.

### Step 2: Clean `PlayingStrategy`
Remove the moved methods from `ai_worker/strategies/playing.py`.
Replace them with delegation:
```python
class PlayingStrategy:
    def __init__(self):
        self.sun_logic = SunStrategy()
        self.hokum_logic = HokumStrategy()
        self.project_logic = ProjectStrategy()

    def _play_sun_strategy(self, ctx):
        return self.sun_logic.get_decision(ctx)
```

### Step 3: Fix The Indentation Bug
While moving `_get_hokum_lead` to `hokum.py`, ensure the logic block at the end (Master Bonus) uses strict 4-space indentation. This is the only "code fix" allowed during the move.

## 3. Critical Constraints
- **Context**: Pass `ctx` everywhere. Do not break the `BotContext` contract.
- **Imports**: If you hit circular imports with `constants.py`, use local imports inside methods temporarily.
- **Verification**: Run `python -m pytest tests/unit/test_sawa_logic.py` after the move to ensure Sawa still works.

## 4. Prompt for Action
**Do not analyze.** Start immediately by creating the component files. This is a pure refactor.
