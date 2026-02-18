# M-F6: Qayd Dispute System & Edge Cases — Task Distribution

> **Phase**: M-F6 | **Started**: 2026-02-18

## Team Assignments

### Claude MAX (Lead)
| Task | Status | Details |
|------|--------|---------|
| DisputeModal orchestrator rewrite | In Progress | Full 6-step wizard matching React DisputeModal.tsx |
| qayd_types.dart | Done | Shared types, enums, constants |
| qayd_main_menu.dart | Done | 3-button menu + waiting state |
| qayd_card_selector.dart | In Progress | Trick browser + card picker |
| qayd_verdict_panel.dart | Pending | Verdict display + evidence cards |
| qayd_footer.dart | Pending | Timer + reporter + back button |
| GameScreen wiring | Pending | Wire DisputeModal + SawaModal into Stack |
| ActionDock edge cases | Pending | Sawa claim, Qayd trigger, Akka buttons |
| Sawa claim flow | Pending | Button in PlayingDock + SawaModal improvements |
| Akka declaration | Pending | HOKUM-only, leading-only button |
| Fast-forward toggle | Pending | Speed up bot turns to 150ms |

### Jules (Module Generation)
| Task | Status | Session ID | Details |
|------|--------|------------|---------|
| Qayd sub-widgets (4 files) | Delegated | `14611954312806542087` | qayd_types, main_menu, card_selector, verdict_panel, footer |

### Antigravity/Gemini (UI Polish)
| Task | Status | Details |
|------|--------|---------|
| Visual QA — Qayd wizard | Pending | Verify all 6 steps look correct |
| Animation polish | Pending | Step transitions, verdict reveal |
| RTL layout verification | Pending | Arabic text alignment in all Qayd widgets |

## Edge Cases Checklist
- [ ] Qayd 6-step: IDLE → MAIN_MENU → VIOLATION_SELECT → SELECT_CARD_1 → SELECT_CARD_2 → RESULT
- [ ] Sawa: claim button → modal → opponents respond → resolve
- [ ] Akka: only in HOKUM, only when leading, requires specific card conditions
- [ ] Kawesh: pre-bid worthless hand → redeal (canDeclareKawesh already in akka_utils.dart)
- [ ] Waraq/Gash: 3 passes + dealer waraq → redeal with dealer rotation
- [ ] Doubling: NORMAL → DOUBLE → TRIPLE → QUADRUPLE → GAHWA
- [ ] Fast-forward: toggle speeds bot actions to 150ms
- [ ] Baloot GP: always 2, immune to all multipliers, added last

## Socket Actions
```
QAYD_TRIGGER          → Start dispute
QAYD_MENU_SELECT      → {option: 'REVEAL_CARDS'|'WRONG_SAWA'|'WRONG_AKKA'}
QAYD_VIOLATION_SELECT → {violation_type: 'REVOKE'|...}
QAYD_SELECT_CRIME     → {suit, rank, trick_idx, card_idx, played_by}
QAYD_SELECT_PROOF     → {suit, rank, trick_idx, card_idx, played_by}
QAYD_CONFIRM          → Acknowledge verdict
QAYD_CANCEL           → Abort at any step
SAWA_CLAIM            → Claim tie
SAWA_RESPONSE         → {response: 'ACCEPTED'|'REFUSED'}
AKKA                  → Declare boss card
```
