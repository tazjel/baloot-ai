# Decision Log

This document tracks significant architectural and product decisions made during the development of the Baloot Web Game.

## Format
### [Date] [Short Title]
**Context:** Why did we need to make a decision?
**Decision:** What did we choose?
**Rationale:** Why did we choose this over alternatives?
**Status:** [Proposed | Accepted | Deprecated]

## Decisions

### 2026-01-07 Winner-Takes-All Projects
**Context:** Baloot rules regarding project (Mashrou) declaration scoring can vary. We needed a definitive rule for how points are awarded when both teams declare projects.
**Decision:** Implemented "Winner-Takes-All" logic. The team with the highest-ranking project scores ALL their projects, while the opposing team scores ZERO for their projects, even if valid.
**Rationale:** This aligns with the standard professional Baloot rules (and the reference implementation "ExternalApp").
**Status:** Accepted

### 2026-01-07 UI Action Bar Control Dock
**Context:** The previous Action Bar had floating buttons that appeared/disappeared based on context, which caused layout shifts and didn't match the "ExternalApp" reference.
**Decision:** Implemented a persistent "Control Dock" at the bottom center of the screen with 4 fixed slots: Projects, Akka, Sawa, and Record.
**Rationale:** Creates a stable UI where buttons occupy fixed mental and spatial slots. Inactive buttons are disabled (greyed out) rather than hidden, providing better affordance and matching the reference video behavior.
**Status:** Accepted
