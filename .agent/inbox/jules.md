# Jules Task Inbox
> **Protocol**: Claude MAX dispatches tasks here. User or Claude triggers via `jules new` CLI.

## How This Works
1. Claude MAX writes task specs in `.agent/delegations/jules/`
2. Claude dispatches via `jules new --repo tazjel/baloot-ai` (piped prompt)
3. Session ID is recorded here
4. When complete, Claude pulls via `jules remote pull --session ID --apply`
5. Claude reviews, tests, and merges

---

## Completed Sessions

| Mission | Session ID | Status | Commit |
|---------|-----------|--------|--------|
| M-MP1 | `18072275693063091343` | ✅ MERGED | `f40901d` |
| M-MP2 | `4458439251499299643` | ✅ MERGED | `f40901d` |

## Active Sessions

| Mission | Session ID | Spec File | Status |
|---------|-----------|-----------|--------|
| M-MP5: ELO Rating Engine | `9718717534070678345` | `M-MP5-elo-rating.md` | 🔄 IN PROGRESS |

## Queued

| Mission | Spec File | Status |
|---------|-----------|--------|
| M-MP8: Leaderboard UI | TBD | ⏳ Not yet written |

---

## Dispatch Command Template
```bash
echo '<prompt text>' | jules new --repo tazjel/baloot-ai
```

## Pull Command Template
```bash
jules remote pull --session <ID> --apply
```
