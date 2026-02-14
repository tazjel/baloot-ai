---
description: Delegate high-level tasks to Claude MAX via Claude Code app. Use for multi-file refactors, system design, full-pipeline integration, and game-theory work.
---

# /claude — Delegate to Claude MAX

Quick workflow for sending high-value work to Claude Opus 4.6 MAX via the Claude Code desktop app.

## Prerequisites
- Claude Code desktop app open with **Baloot AI folder selected**
- Claude reads `CLAUDE.md` automatically for project context

## Task Categories

### 🔴 Multi-File Refactor
Best for: sun/hokum dedup, brain.py redesign, architecture changes
```
Read sun.py and hokum.py completely. Extract the shared follow/lead logic 
into a unified play_engine.py, keeping only mode-specific overrides.
Update both files to import from the new shared module.
Run tests to verify nothing breaks.
```

### 🟡 Full-Pipeline Integration
Best for: new strategy module + wiring + tests in one shot
```
Read .claude/task_XX_module_name.md for the spec.
Read sun.py, hokum.py, and brain.py for integration patterns.
1. Generate the module in ai_worker/strategies/components/
2. Wire it into sun.py and hokum.py (try/except wrapping)
3. Write unit tests in tests/bot/
4. Verify all tests pass
```

### 🟢 Game-Theory Strategy
Best for: letting Claude DESIGN the optimal play strategy
```
You are an expert Baloot player. Read the current bot strategy in sun.py.
Identify the top 3 strategic mistakes. For each:
1. Explain the game-theory error
2. Design a better approach
3. Implement the fix
4. Write tests proving the improvement
```

### 🔵 Test Architecture
Best for: comprehensive edge-case coverage
```
Read game.py, scoring_engine.py, and validation.py.
Generate a test suite covering: [specific areas].
Target: 50+ test cases across 3 test files.
```

## Prompt Best Practices
1. **Always say "Read [file]"** — Claude MAX shines when given real source code, not summaries
2. **Ask it to REASON first** — "Analyze the decision flow, then implement"
3. **Request multi-file output** — module + integration + tests in one shot
4. **Let it critique** — "What would you improve in the current approach?"
5. **Use Code mode** — Claude Code directly edits files in the repo

## After Claude Finishes

// turbo
1. Check git diff:
```
git diff --stat
```

// turbo
2. Run tests:
```
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q
```

3. Review changes in Antigravity
4. Commit when satisfied:
```
git add -A && git commit -m "feat: [description of Claude's work]"
```
