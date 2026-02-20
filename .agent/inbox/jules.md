# Jules Task Inbox
> **Protocol**: Claude MAX dispatches tasks here. User or Claude triggers via `jules new` CLI.
> **Updated**: 2026-02-20 (night)

## How This Works
1. Claude MAX writes task specs in `.agent/delegations/jules/`
2. Claude dispatches via Jules MCP `create_session`
3. Session ID is recorded here
4. When complete, Claude reviews PR, tests, and merges
5. Antigravity runs QA verification

---

## Completed Sessions

| Mission | Session ID | Status | Commit |
|---------|-----------|--------|--------|
| M-MP1 | `18072275693063091343` | MERGED | `f40901d` |
| M-MP2 | `4458439251499299643` | MERGED | `f40901d` |
| M-MP5 | `9718717534070678345` | COMPLETED — needs pull | — |

## Active Sessions

| Mission | Session ID | Spec File | Status |
|---------|-----------|-----------|--------|
| M-MP8: Leaderboard UI | `13581679709388677131` | `M-MP8-leaderboard-ui.md` | RUNNING — auto-PR enabled |
| M-MP9: Integration Tests | `3626643731020681379` | `M-MP9-integration-tests.md` | RUNNING — auto-PR enabled |

## Queued

_None — all current specs dispatched._

---

## Dispatch Command Template
```bash
# Via Jules MCP tools (preferred)
jules_create_session(repoOwner="tazjel", repoName="baloot-ai", prompt="...", autoCreatePR=true)
```

## Pull Command Template
```bash
# Check PR on GitHub, review diff, then merge
gh pr list --repo tazjel/baloot-ai
gh pr merge <number> --squash --repo tazjel/baloot-ai
```
