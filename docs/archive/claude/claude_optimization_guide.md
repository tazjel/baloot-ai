# Claude Interaction Guide: High-Efficiency Coding

This guide is designed to maximize output quality from Claude while minimizing token usage and context window consumption. Use these strategies when delegating tasks.

## 1. The "No-Fluff" Protocol (Token Saving)

**Instruction to Claude:**
> "Act as a Senior Python Engineer. When I ask for code, provide **only** the necessary code block or diff. Do not include introductory text ('Here is the code...'), conversational filler, or summaries unless explicitly asked. Use `...` for unchanged sections."

**Why:** eliminating conversational filler saves 10-20% of tokens per response.

## 2. Context Loading Strategy

Instead of pasting entire files:
1.  **Interfaces/Signatures**: Paste only the class definition and method signatures for context.
2.  **Specific Logic**: Paste only the specific function/method you need to change.
3.  **Dependencies**: valid imports are assumed; do not ask for imports unless adding new libraries.

**Example Prompt:**
> "I need to fix `calculate_score` in `game_engine`. Here is the current implementation (snippet). Here is the `Score` class definition (snippet). The error is `IndexError: list index out of range`. Fix the function."

## 3. Requesting Changes via Diffs

Always ask for **Git-style diffs** or **Unified Diffs** rather than full file rewrites.

**Prompt Pattern:**
> "Refactor `_handle_bidding` to support the new `Hijack` rule. Return the changes as a unified diff format I can apply with `git apply` or manually patch."

## 4. The "Chain of Thought" Trap

**Avoid**: "Think step-by-step and explain..." (for simple tasks).
**Prefer**: "Plan the logic in 3 bullet points, then write the code."

**Why:** Extensive reasoning fills the context window. Keeping the plan separate and concise forces focus without verbosity.

## 5. Task-Specific Templates

### A. Bug Fixing
> **Role**: Debugger
> **Input**: Error Trace + Relevant Function Code
> **Constraint**: Fix the logic error. Do not change variable names or style unless necessary.
> **Output**: Corrected function code only.

### B. Refactoring
> **Role**: Architect
> **Input**: Class/Module Source
> **Goal**: Extract `LogicX` into a new strategy component.
> **Constraint**: Preserve the `ctx` (BotContext) interface.
> **Output**: 
> 1. New Component Class (`new_file.py`)
> 2. Modified Original Class (Diff view)

### C. Unit Tests
> **Role**: QA Engineer
> **Input**: Function to test
> **Goal**: Create pytest cases for edge cases: [Edge Case 1], [Edge Case 2].
> **Constraint**: Use `mock` for external dependencies (Redis, DB).
> **Output**: Test function code only.

## 6. Project-Specific "System Prompt"

Keep this snippet handy to paste at the start of a session:

```markdown
**System Context:**
- Project: Baloot AI (Saudi Card Game)
- Stack: Python 3.9+, Redis, SQLite
- Key Objects: 
  - `BotContext`: Holds game state snapshot.
  - `Game`: Central engine.
  - `Card`: Standard 52-card deck subset.
- Interaction Style: Direct, Code-First, Concise.
- Forbidden: changing `sawa.py` logic without verifying `test_sawa_logic.py`.
```

## 7. Handling "Lost in Context"

If Claude starts hallucinating or losing track:
1.  **Stop**: Do not argue.
2.  **Reset**: Start a new chat.
3.  **Refine**: Provide *less* but more *focused* context.

---
*Use this guide to keep the AI focused on "Smart Work" — high-leverage logic and architecture changes, rather than boilerplate generation.*
