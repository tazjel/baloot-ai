---
description: Initialize the agent session efficiently with Git sync check and conflict prevention.
---

# Start Session (Lean Boot v3)

// turbo-all

Boot the agent's context using the **"High Value, Low Token"** strategy. Includes Git sync, multi-agent awareness, and conversation continuity.

## 1. Environment Constraints

- **OS**: Windows · **Shell**: PowerShell (no `export`, no `&&`).
- Use `;` or separate commands. Paths use `\` but `/` works in code.

## 2. Git Sync Check

- Run `git status --short` and `git log -5 --oneline`.
- **If uncommitted changes**: Summarize briefly → Ask: *"Commit checkpoint?"* or *"Proceed as-is?"*
- **If clean**: Continue silently.
- **If remote is ahead**: Warn user, suggest `git pull`.

## 3. Load Essential Context (Parallel Reads)

Read these files **in parallel** (all reads are independent):

| File | When to Read | Goal |
|------|-------------|------|
| `.agent/knowledge/developer_tips.md` | **Always** | Avoid known pitfalls |
| `.agent/knowledge/handoff.md` | **Always** (check if exists first) | Cross-agent context |
| `CODEBASE_MAP.md` | Only if task involves unfamiliar code | File structure overview |

### Handoff Freshness Check
- Run `git log -1 --format="%ai" -- .agent/knowledge/handoff.md` to get last modified date.
- **< 48 hours old**: Summarize key points to user (mark as 🟢 Fresh).
- **> 48 hours old**: Note it's stale (mark as 🟡 Stale) — still mention highlights but don't prioritize.

## 4. Multi-Agent Awareness

Check for recent work by other agents:

- **Conversation History**: Scan the provided conversation summaries for the last 24-48 hours. Note any ongoing themes (e.g., "You've been working on Qayd rules and test coverage recently").
- **Jules Sessions** (optional, only if relevant): Run `mcp_jules_list_sessions` to check for pending PRs or completed work.
- **Claude Desktop**: If `handoff.md` mentions Claude work, summarize it.

## 5. What NOT to Do

- ❌ Read `current_state.md` or full project handbook (too large).
- ❌ List large directories (`node_modules`, `venv`, `__pycache__`).
- ❌ Auto-run `/check-health` (user can request it).
- ❌ Run any servers or build steps.
- ❌ Read `CODEBASE_MAP.md` unless the task specifically requires navigation.

## 6. Session Brief

Present a concise brief to the user:

### Format
```
## 🚀 Session Boot Complete

**Git Status**: [Clean ✅ | X uncommitted changes ⚠️]
**Handoff**: [🟢 Fresh (date) | 🟡 Stale (date) | ❌ Not found]
**Recent Activity**: [1-line summary of last 2-3 conversations]

### 💡 Developer Tips Reminders
- [Top 2-3 most relevant tips for the session]

### 📋 Suggested Tasks
1. [High-priority task from handoff/tips/recent conversations]
2. [Second priority]
3. [Third priority / exploratory]

### ⚡ Quick Commands
| Command | Purpose |
|---------|---------|
| `/start` | Launch full game stack |
| `/check-health` | Verify Redis + Backend + Frontend |
| `/major-test` | Run 4-bot simulation |
| `/dashboard` | Open Command Center |
| `/missions` | Generate improvement missions |
| `/finalize-session` | End session + update docs |
| `/claude` | Delegate to Claude MAX |

What would you like to work on?
```

### Rules for the Brief
- Keep the entire output under ~30 lines.
- **Do NOT** dump full file contents — summarize.
- Prioritize actionable items over historical context.
- If this is a **new conversation** (no prior task.md): Suggest starting with `/missions` or ask what's on the user's mind.
