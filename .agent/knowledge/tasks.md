# Active Task Distribution — 2026-02-18

> **M-F7**: ✅ Tests pass (130/130) | **M-F8**: 🔄 Claude building | **Protocol**: multi-agent.md active

---

## Claude MAX — M-F8: Online Multiplayer
| Task | Status | Details |
|------|--------|---------|
| WebSocket service rewrite | 🔄 In Progress | Socket.IO client, connect/disconnect, reconnect |
| Room management | ⏳ Next | Create/join/leave room, room state sync |
| State sync layer | ⏳ Next | Server→client state rotation + merge |
| Reconnection handler | ⏳ Next | Auto-reconnect with state recovery |

---

## Jules — Waiting for Next Task
| Task | Status | Session ID | Details |
|------|--------|------------|---------|
| M-F7 Tests | ✅ Done | `15951593649281280163` | 4 files, 28 tests, merged |
| M-F8: Connection Status Widget | ⏳ Assigned below | — | New widget file |

---

## Antigravity — Tasks 6-9 (Visual QA + Housekeeping)

| # | Task | Status | Details |
|---|------|--------|---------|
| 6 | Visual QA — Qayd wizard | 🔲 Do Now | Launch app, trigger Qayd (⚖ button), walk through all 6 steps. Verify: menu renders 3 options, card selector shows trick browser, verdict panel shows penalty, footer has timer circle |
| 7 | Visual QA — Edge buttons | 🔲 Do Now | Verify in PlayingDock: Akka (⭐ medal icon, HOKUM+leading only), Fast-forward (⏩/⏸ toggle). In BiddingDock: Kawesh (🔄 refresh icon, only when hand has no court cards) |
| 8 | RTL verification | 🔲 Do Now | Check Arabic text alignment in: Qayd menu labels, verdict messages, toast "بلوت! لديك الملك والملكة", Kawesh "كوش" button, system messages |
| 9 | Update MEMORY.md | 🔲 Do Now | Set Flutter tests to **130 passing**. Add M-F7 to completed missions. Add Jules CLI info: `npm i -g @google/jules`, owner=`tazjel` |

### Antigravity Commands
```powershell
# Visual QA — launch app
cd "C:/Users/MiEXCITE/Projects/baloot-ai/mobile"
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" run -d chrome

# Verify tests still green
"C:/Users/MiEXCITE/development/flutter/bin/flutter.bat" test
```

### Success Criteria
- All 6 Qayd wizard steps visually correct
- Akka/Kawesh/FF buttons appear at correct times
- Arabic text reads right-to-left, no clipping
- MEMORY.md updated with 130 test count + M-F7 completion

---

## File Locks
None active. See `.agent/knowledge/file_locks.md`.
