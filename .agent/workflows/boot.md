---
description: Initialize the agent session efficiently with Git sync check and conflict prevention.
---

# Start Session (Lean Boot v4)

// turbo-all

Boot the agent context fast. **"High Value, Low Token"** — zero fluff, only what matters.

## 1. Git Sync (single compound command)

Run all at once:
```powershell
git status --short; git log -3 --oneline; git log -1 --format="%ai" -- .agent/knowledge/handoff.md
```

- **Uncommitted changes?** → Summarize briefly, ask: *"Commit checkpoint?"* or *"Proceed?"*
- **Clean?** → Continue silently, don't mention it.
- **Remote ahead?** → Warn, suggest `git pull`.
- Note the handoff date from the third command for Step 2.

## 2. Load Context (parallel reads)

Read **both** in parallel — they are independent:

1. `.agent/knowledge/developer_tips.md` — Pitfalls & rules.
2. `.agent/knowledge/handoff.md` — Cross-agent context.

**Handoff freshness** (from Step 1 date output):
- **< 48h** → 🟢 Fresh — summarize key points.
- **> 48h** → 🟡 Stale — mention but deprioritize.
- **Not found** → ❌ Skip.

## 3. Multi-Agent Awareness

- **Conversation summaries** (already provided): Scan last 24-48h for recurring themes. One-line summary.
- **Jules**: Only check `mcp_jules_list_sessions` if handoff explicitly mentions pending Jules PRs.
- **Claude**: Only mention if handoff references active Claude work.

## 4. Guardrails

- ❌ Don't read `current_state.md`, project handbook, or `CODEBASE_MAP.md`.
- ❌ Don't list dirs, run servers, build, or auto-run `/check-health`.

## 5. Session Brief

Output this to the user — **under 15 lines**:

```
## 🚀 Session Boot

**Git**: [Clean ✅ | N changes ⚠️] · **Handoff**: [🟢/🟡/❌ + date]
**Recent**: [1-line summary of last 2-3 conversations]

### 💡 Tips
- [Top 2-3 developer tips]

### 📋 Suggested
1. [High-priority from handoff/conversations]
2. [Second priority]
3. [Exploratory]

What would you like to work on?
```

**Rules**: Don't dump file contents. Prioritize actionable over historical. New conversation? Suggest `/missions`.
