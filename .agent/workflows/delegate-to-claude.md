---
description: Delegate AI module development to Claude Opus — audit gaps, craft prompts, save as copy-paste files, integrate returned code, verify with tests.
---

# Delegate AI Tasks to Claude

> **⚠️ DEPRECATED**: This workflow uses the old copy-paste method.  
> For Claude MAX (Code mode), use **`/claude`** instead — Claude directly reads/writes files.

## When to Use This Workflow
Only use this if Claude Code is unavailable and you must use claude.ai web interface.

---

## Legacy Method: Build → Paste → Download → Integrate

### Step 1: Build the Batch Prompt

// turbo
1. Auto-assemble task files into a single prompt:
```
python .claude/build_prompt.py --range 17-20
```

This reads `.claude/task_*.md` files in the given range, wraps them in global Baloot context, and produces **`.claude/BATCH_PROMPT.md`**.

### Step 2: Send to Claude (ONE paste)

2. Open `.claude/BATCH_PROMPT.md` → **Ctrl+A → Ctrl+C**
3. Paste into **Claude Opus** (claude.ai)
4. Claude generates each module as a **downloadable `.py` artifact** in the sidebar
5. If Claude hits its limit mid-batch, send "continue" — it picks up where it stopped

### Step 3: Download Artifacts to Staging

6. In Claude's sidebar, each `.py` file has a download button
7. Download ALL `.py` files to: **`.claude/staging/`**

### Step 4: Tell Antigravity to Integrate

8. Say: **"Review and integrate staged Claude modules"**

### Step 5: Verify

// turbo
9. Run the test suite:
```
python -m pytest tests/bot/ tests/game_logic/ --tb=short -q
```

---

## Preferred Method: /claude (Claude MAX Code Mode)
See `/claude` workflow — Claude directly edits files, no copy-paste needed.
