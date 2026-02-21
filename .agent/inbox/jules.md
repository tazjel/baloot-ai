# Jules Task Inbox
> **Protocol**: Claude MAX dispatches tasks here. User or Claude triggers via `jules new` CLI.
> **Updated**: 2026-02-21

## How This Works
1. Claude MAX writes task specs in `.agent/delegations/jules/`
2. Claude dispatches via Jules MCP `create_session`
3. Session ID is recorded here
4. When complete, Claude reviews PR, tests, and merges
5. Antigravity runs QA verification

---

## Queued Tasks

### 🔴 QUEUED — Bot Turn Handler Unit Tests
**Priority**: MEDIUM | **Spec**: `.agent/delegations/jules/bot-turn-handler-tests.md`
**Description**: Create unit tests for the new `mobile/lib/state/bot_turn_handler.dart` file.
This is a critical file for offline bot AI play that currently has zero test coverage.

---

## Completed Sessions

| Mission | Session ID | Status | Commit |
|---------|-----------|--------|--------|
| M-MP1 | `18072275693063091343` | MERGED | `f40901d` |
| M-MP2 | `4458439251499299643` | MERGED | `f40901d` |
| M-MP5 | `9718717534070678345` | COMPLETED — no PR | — |
| M-MP8 | `13581679709388677131` | COMPLETED — no PR | — |
| M-MP9 | `3626643731020681379` | COMPLETED — no PR | — |
| M-MP11 | `4909654043665946126` | FAILED | — |

## Active Sessions

_None — awaiting dispatch._

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
