---
description: Delegate AI module development to Claude Opus — audit gaps, craft prompts, save as copy-paste files, integrate returned code, verify with tests.
---

# Delegate AI Tasks to Claude Opus

This workflow creates self-contained task prompts for Claude Opus, saves them as copy-paste-ready `.md` files, and handles integration of the returned code.

## Phase 1: Audit & Identify Gaps

1. List all existing AI components:
```
ls ai_worker/strategies/components/
```

2. Read the strategy files to understand current capabilities:
   - `sun.py`, `hokum.py` — play strategies
   - `bidding.py` — bid decisions
   - `base.py` — shared logic (follow-suit, trash)
   - `signaling.py` — partner communication

3. Identify **strategic blind spots** — areas where the bot plays mechanically instead of intelligently. Look for:
   - Ad-hoc inline calculations that should be modules
   - Missing decision layers (e.g. no point awareness, no trump strategy)
   - Existing modules not connected to each other
   - Hardcoded thresholds without game-state awareness

4. Prioritize gaps by **impact**: which gap, if filled, would most improve win rate?

## Phase 2: Craft Task Prompts

For each task, create a `.md` file in `.claude/` with this structure:

```markdown
Write a single self-contained Python module: `module_name.py`

[1-2 sentence description of what this module does and why it matters]

Return ONLY the Python code, no explanation.

## Function Signature
[Exact function signature with typed parameters and return dict spec]

## Constants
[Any game constants the module needs — copy exactly]

## Logic Rules
[Table or bullet list of decision rules with conditions → actions]

## Requirements
- Pure function, no imports beyond stdlib
- Include module docstring
- Hand cards have `.rank` and `.suit` attributes
- [Any other constraints]
```

**Key principles for good prompts:**
- **Self-contained**: Claude should need ZERO context beyond the prompt
- **Explicit return type**: Show the exact dict structure expected
- **Copy constants**: Don't reference external files — paste the values
- **Logic tables**: Rules as tables are clearer than prose
- **No imports**: Pure functions are easier to integrate

5. Save each task as `.claude/task_XX_module_name.md`
// turbo

## Phase 3: User Copies & Pastes

The user opens each file, Ctrl+A → Ctrl+C, pastes into Claude Opus, and pastes the returned Python code back here.

## Phase 4: Integrate Returned Code

When the user pastes Claude's output:

// turbo
6. Save the code to `ai_worker/strategies/components/<module_name>.py`

7. Find the best integration point in the existing strategy code:
   - **Lead logic** → wire into `_get_hokum_lead()` or `_get_sun_lead()`
   - **Follow logic** → wire into `_hokum_card_play()` or `_sun_card_play()`
   - **Bidding** → wire into `bidding.py`
   - **Defense** → wire into `_get_defensive_lead_*()`
   - **Context** → add to `BotContext.py` if it needs game state access

8. Wire the new module:
   - Add `from ai_worker.strategies.components.<module> import <function>` at the call site
   - Replace any ad-hoc inline logic that the module supersedes
   - Add `logger.debug(f"[TAG] {result['reasoning']}")` for observability
   - Preserve existing behavior as fallback

## Phase 5: Verify

// turbo
9. Run the full test suite:
```
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q
```

10. Confirm **302+ passed, 0 failures** (test count may grow over time)

11. Report status to user with a scorecard table:
```
| # | Module | Status |
|---|--------|:------:|
| X | Module Name | ✅ Live |
```

## Tips
- **Batch tasks**: Design 4 tasks at a time — enough for a focused session
- **Order matters**: Independent modules first, orchestration layer last
- **Test after each**: Never integrate 2 modules without testing between them
- **Log everything**: Every new module should log its reasoning for dashboard visibility
