# ⚡ External Skills Cheat Sheet

**"How do I use these efficiently?"**
Don't memorize 600 skills. Just use this map. When you have a task, ask the Agent to **"Load the [Skill Name] skill"**.

## 🎯 Top 10 Skills for Baloot AI

| If you are doing... | 🔮 **Invoke this Skill** | **Why?** |
| :--- | :--- | :--- |
| **Writing Code** | `clean-code` | Enforces DRY, KISS, and no-nonsense variable names. |
| **Frontend Work** | `react-best-practices` | Prevents `useEffect` loops and optimizes re-renders. |
| **Backend Logic** | `python-pro` | Pythonic idioms, type hinting, and performance tips. |
| **Debugging** | `debugging-strategies` | Systematic root-cause analysis (Rubber Ducking). |
| **Refactoring** | `architecture-patterns` | Helps split massive files (like `game.py`) cleanly. |
| **UI Polishing** | `frontend-design` | Principles for spacing, typography, and "WOW" factor. |
| **Committing** | `git-advanced-workflows` | Ensures clean history and atomic commits. |
| **Security Check** | `security-auditor` | Scans for injection, serialization risks, and secrets. |
| **Testing** | `tdd-workflow` | Guides you through Red-Green-Refactor cycles. |
| **Slow Code?** | `performance-profiling` | Identifies bottlenecks in Python or React. |

---

## 🚀 "Skill-Based Prompting" Strategy

Instead of micro-managing me, give me a **Role** and a **Skill**.

### ❌ Weak Prompt
> "Fix the bug in the card rendering where it flickers."

### ✅ Power Prompt (Efficiency Mode)
> "Act as a **Frontend Expert**. Load the **`react-best-practices`** skill. Fix the card flickering in `HandFan.tsx` and ensure no unnecessary re-renders."

### ✅ Power Prompt (Refactor Mode)
> "Load **`clean-code`**. Audit `game_engine/logic.py` and list the top 3 violations of SRP (Single Responsibility Principle)."

---

## 🛠️ Specialized Scenarios

-   **"The Game is Lagging"** -> `performance-profiling` + `python-performance-optimization`
-   **"I want to add a new Feature"** -> `feature-development` (General) or `checklist-driven-development`
-   **"Verify my Logic"** -> `unit-testing` or `verification-strategies`

## 📍 Location
All skills are located in `.agent/skills/external/skills/[skill-name]`.
You can ask me to reading them anytime: "Read the instructions for `react-native-architecture`".
