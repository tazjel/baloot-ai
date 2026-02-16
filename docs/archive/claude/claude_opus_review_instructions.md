# Instructions for Claude Opus 4.6 - Baloot AI Codebase Review

## Context
You are an expert Game Backend and Frontend Engineer auditing the "Baloot AI" codebase. Your goal is to review the core game logic implementation for correctness, state consistency, and race conditions.

**CONSTRAINT:** IGNORE all "Visionary Studio", "AI Studio", "YOLO", and "AI Training" components. Focus ONLY on the actual card game mechanics (Bidding, Playing, Scoring, Projects, Qayd/Dispute).

## Codebase Scope

### 1. Backend Game Logic (`game_engine/logic/`)
*   `game.py`: Main state machine. Check phase transitions (BIDDING -> PLAYING -> SCORING).
*   `bidding_engine.py`: Review Sun/Hokum logic, doubling (Moshara, etc.), and blind bidding (Gablak).
*   `trick_manager.py`: Check turn order, card validity rules (void suits), and trick winner calculation.
*   `project_manager.py`: Validate logic for Sira, Baloot, 100, 400 declarations.
*   `scoring_engine.py`: Verify point calculations (26/16 pts), penalties, and game-winning thresholds.

### 2. Frontend Game Components (`frontend/src/`)
*   `components/Table.tsx`: Main game board rendering and orchestrator.
*   `components/HandFan.tsx`: Player hand interaction.
*   `components/ActionBar.tsx`: Bidding controls and player actions.
*   `components/DisputeModal.tsx`: **[CRITICAL]** The "Qayd" (Forensic Challenge) UI.
*   `components/SawaModal.tsx` & `ProjectSelectionModal.tsx`: Declaration interfaces.
*   `hooks/useGame.ts`: Client-side state management loop.

---

## Functional Specification: Qayd (Forensic Challenge)
**Use this specification as the STRICT Source of Truth for validating the Qayd logic.**

### 1. Functional Overview
This system replicates the **source platform** forensic experience.
**Core Mandate:** Cheating remains "hidden" until physically challenged. The system allows players to challenge violations, pause the game, and adjudicate penalties.

### 2. The Qayd UX Cycle (5-Step Flow)
The system follows a strict 5-step forensic cycle.

#### Step 1: Trigger Menu (`MAIN_MENU`)
A small popup with 3 initial options:
1.  **Reveal Cards** (كشف الأوراق)
2.  **Wrong Sawa** (سوا خاطئ)
3.  **Wrong Akka** (أكة خاطئة)

#### Step 2: Violation Selection (`VIOLATION_SELECT`)
A top bar menu displaying specialized violation types as toggles:
*   **Revoke (قاطع):** Failure to follow suit.
*   **Trump in Double (ربع في الدبل):** Illegal trumping in doubled game.
*   **Didn't Overtrump (ما كبر بحكم):** Playing lower trump when holding higher.
*   **Didn't Trump (ما دق بحكم):** Not trumping when void in suit.

#### Step 3: First Card Selection (`SELECT_CARD_1`) *[Implicit]*
*The user selects the first card involved in the violation (The "Crime").*
*   **Visuals:** This card is highlighted with a **Pink Ring**.
*   **Instruction:** "اختر الورقة التي تم الغش بها" (Select the card used for cheating).

#### Step 4: Second Card Selection (`SELECT_CARD_2`)
*The user selects the second card that proves the violation (The "Proof").*
*   **Visuals:** The first card remains **Pink**. The second card selection triggers a **Green confirmation text**.
*   **Instruction:** "اذهب وابحث عن الورقة الثانية التي كشفت الغش" (Go and find the second card that revealed the cheating).

#### Step 5: Result Adjudication (`RESULT`)
A wide banner displays the final verdict.
*   **Correct Qayd:** Green Banner "قيد صحيح"
*   **Wrong Qayd:** Red Banner "قيد خاطئ"
*   **Behavior:**
    *   The final `RoundResultsModal` is displayed.
    *   Backend triggers `auto_restart_round` (2-second delay).
    *   Frontend sends `QAYD_CONFIRM` to acknowledge and sync the restart.

### 3. UI/UX Standards
*   **Visual Identity:** Solid Dark Grey (`#404040`) background for overlays. Font: **Tajawal**.
*   **Visual Evidence:** Manual accusations use specific rings (Pink for Crime, Green for Proof).
*   **Timers:** 60s for Human Reporter, 2s for AI/Remote Reporter.

---

## Review Tasks
1.  **Phase Transition Integrity:** Are there gaps where the game hangs between phases (e.g., after a Qayd resolution)?
2.  **Race Conditions:** Can a player act (bid/play) while the server is processing a previous state?
3.  **Qayd Logic:** Does the `DisputeModal` correctly implement the 5-step flow defined above? Does the backend correctly rollback/penalize?
4.  **Score Verification:** Are points for "Projects" (Sira/Baloot) added correctly to the raw card scores?

## Output Format
1.  **Critical Bug List:** Identify specific logic flaws with file/line references.
2.  **State Management:** Suggest improvements for syncing backend state with frontend animations.
3.  **Deadlock Analysis:** Identify potential freezes in the "Qayd" flow.
4.  **Strategic Recommendation:** **Given the current state of the core logic, would you suggest rewriting these specific modules (Game Engine/Frontend Logic) from scratch to ensure stability?** Please provide your reasoning.
