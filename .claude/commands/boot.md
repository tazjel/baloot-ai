Session kickstart for Baloot AI. Run these steps in order:

1. Read CLAUDE.md for project rules
2. Read your memory file at `C:\Users\MiEXCITE\.claude\projects\C--Users-MiEXCITE-Projects-baloot-ai\memory\MEMORY.md`
3. Read the agent status board at `.agent/knowledge/agent_status.md` — check for completed work from Antigravity and any pending task assignments
4. Read the mission brief at `.agent/next-session-brief.md`
5. Run the test suite: `python -m pytest tests/bot/ tests/game_logic/ --tb=short -q`
6. Check git status for uncommitted changes: `git status --short`
7. Check for TypeScript errors: `cd frontend && npx tsc --noEmit`


Then present a concise status report:

| Check | Status |
|-------|--------|
| Tests | X passing / Y failing |
| TypeScript | X errors |
| Git | clean / N uncommitted changes |
| Agent Status | Antigravity: [status] / Pending tasks: [count] |
| Last completed mission | ... |
| Next mission | ... |

If there are failing tests or uncommitted work, flag them.
Then state what the next mission is and its key tasks, and ask: "Ready to start? Or would you like to work on something else?"

Do NOT start any work automatically. Just report and wait for instructions.
