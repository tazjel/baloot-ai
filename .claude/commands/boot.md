Session kickstart for Baloot AI. Run these steps in order:

## 1. Context Load (parallel)
Read ALL of these simultaneously:
- `CLAUDE.md` — project rules
- Your memory file at `C:\Users\MiEXCITE\.claude\projects\C--Users-MiEXCITE-Projects-baloot-ai\memory\MEMORY.md`
- Agent status board at `.agent/knowledge/agent_status.md`
- Mission brief at `.agent/next-session-brief.md`
- Task board at `.agent/knowledge/tasks.md` (if it exists)

## 2. Health Check (parallel)
// turbo-all
Run ALL of these simultaneously:
- `git status --short`
- `git log --oneline -5` (recent commits for context)

## 3. Flutter Health
// turbo-all
Run this command:
- `cd mobile && flutter analyze 2>&1 | tail -3` (Flutter analysis — last 3 lines only)

## 4. Stale Branch Check
- `git branch --list` — flag any non-main branches that might be leftover

## 5. Status Report
Present a concise dashboard:

```
## Boot Report — [date]

### Health
| Check          | Status                           |
|----------------|----------------------------------|
| Python Tests   | X passing / Y failing            |
| Flutter Tests  | X passing / Y failing            |
| Flutter Analyze| X errors / clean                 |
| TypeScript     | X errors / clean                 |
| Git            | clean / N uncommitted changes    |
| Branches       | main only / [list extras]        |

### Recent Commits (last 5)
[one-liner list from git log]

### Agent Status
| Agent       | Status        | Last Action                |
|-------------|---------------|----------------------------|
| Claude MAX  | [status]      | [what was last done]       |
| Antigravity | [status]      | [what was last done]       |
| Jules       | [status]      | [any pending PRs?]         |

### Mission Status
- **Completed**: [count] / 20 Flutter missions
- **What's left**: [manual steps or next work items]
- **Blockers**: [any blockers from brief or agent board]
```

## 6. Alerts
Flag anything that needs attention:
- Failing tests (with names)
- Uncommitted changes (with file list)
- Stale branches
- Pending Jules PRs to cherry-pick
- Outdated agent status (>48h since last update)
- Any discrepancies between memory and actual state (test counts, etc.)

## Rules
- Do NOT start any work automatically. Just report and wait for instructions.
- Do NOT fix failing tests — just report them.
- Be concise. The dashboard should fit on one screen.
- If a health check command fails to run (missing tool, network issue), report it as "SKIPPED" with reason.
- After the report, ask: "Ready to start? What would you like to work on?"
