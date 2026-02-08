# Claude Code Review & Intelligence Protocol

Use this guide to direct Claude to perform deep architectural reviews rather than surface-level linting.

## 1. The "Architect" Persona

**System Prompt / Role Definition:**
> "Act as a Senior Full-Stack Architect (Python/React). Your goal is to identify **structural weaknesses, race conditions, and UX gaps**. Do not focus on PEP8 or minor syntax unless it causes bugs. Prioritize: 1. Correctness, 2. Performance, 3. Maintainability."

## 2. Backend Review (Python/FastAPI/Redis)

**Focus Areas:**
*   **Concurrency**: Baloot is a real-time game. usage of Redis locks (`lock_manager`) and atomic operations.
*   **Game State Integrity**: Ensuring `Game` object serialization/deserialization doesn't lose data.
*   **Bot Logic**: Optimizing `check_sawa`, `check_akka`, and decision trees in `strategies/`.

**Prompt Template:**
> "Review `[filename.py]`. Focus on **Race Conditions** and **State Consistency**.
> 1.  Are there any windows where two players could act simultaneously and corrupt the state?
> 2.  Are we over-fetching data from Redis?
> 3.  Suggest a more efficient data structure for [specific component]."

## 3. Frontend Review (React)

**Focus Areas:**
*   **Render Cycles**: Identifying unnecessary re-renders in the Game Board.
*   **State Sync**: Handling `WebSocket` events vs local state (Zustand/Context).
*   **UX/UI Polish**: "Juice" (animations, feedback) and error recovery.

**Prompt Template:**
> "Review `[Component.tsx]`. Focus on **Render Performance** and **User Feedback**.
> 1.  Is `useEffect` cleaning up listeners correctly?
> 2.  Are we handling WebSocket disconnection/reconnection gracefully?
> 3.  Propose a CSS/Framer Motion animation to make [Action X] feel more impactful."

## 4. "Intelligent" Suggestions (The 'Spark' Prompts)

Use these to get creative solutions:

*   **The Simplifier**: "This function `calculate_score` is 100 lines long. Rewrite it effectively using helper functions or a Strategy pattern. Keep it under 40 lines."
*   **The Devil's Advocate**: "I plan to implement [Feature X] this way. Tell me 3 reasons why this might fail in production (lag, crashes, cheats)."
*   **The User Advocate**: "Look at the `GameUI` component. What visual queues are missing that would help a new player understand what's happening?"

## 5. Review Output Format

Enforce this format to keep Claude concise:

> **Report Format:**
> *   **Critical Issues**: (Bugs, Races, Security) - Fix Immediately.
> *   **Architecture Debt**: (Tight coupling, poor separation) - Refactor soon.
> *   **Nitpicks**: (Variable names, comments) - Ignore for now.
> *   **Smart Suggestion**: One high-impact improvement idea.

## 6. Example: Reviewing the Bidding Logic

**User:**
"Review `game_engine/logic/bidding_engine.py`. Focus on the 'Priority Hijack' rule. Ensure a player cannot bid if it's not their turn or if they don't have priority."

**Claude (Expected):**
*   **Critical**: `check_turn` validation is missing inside the `hijack` block.
*   **Architecture**: Logic for 'priority' is duplicated in `TurnManager`. Move to shared helper.
*   **Smart Suggestion**: Use a `PriorityQueue` for managing potential bidders instead of a list.

---
*Use this protocol to leverage Claude's reasoning capabilities for valid engineering improvements.*
