"""Build the master Claude Opus prompt from all task_*.md files.

Usage:
    python .claude/build_prompt.py

Reads all .claude/task_*.md files (sorted by number), wraps them in the
master prompt template with global context, and writes the result to
.claude/BATCH_PROMPT.md — ready for a single copy-paste into Claude.
"""
import os
import glob
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_GLOB = os.path.join(SCRIPT_DIR, "task_*.md")
OUTPUT = os.path.join(SCRIPT_DIR, "BATCH_PROMPT.md")


def parse_range(arg: str) -> tuple[int, int]:
    """Parse '13-16' into (13, 16)."""
    parts = arg.split("-")
    return int(parts[0]), int(parts[1])

HEADER = r"""# Baloot AI — Batch Module Generation

You are generating Python modules for a Baloot AI strategy system.

## Instructions
Below are multiple task specifications separated by `---TASK---` markers. For EACH task:
1. Read the specification carefully
2. Write the complete Python module
3. Create it as a **downloadable Python file artifact** (`.py` file)

**IMPORTANT:** Create each module as a separate `.py` file artifact — NOT as code blocks in chat.
Name each artifact exactly as specified in the task (e.g. `opponent_model.py`).

Process ALL tasks below. Do NOT stop after one. If you hit your limit, finish the current module completely before stopping. If you stop, I will say "continue" and you should pick up with the next task.

---

## GLOBAL CONTEXT (applies to ALL tasks)

**Game:** Baloot — Saudi Arabian trick-taking card game
- 4 players in 2 teams (Bottom+Top vs Right+Left)
- 32 cards: ranks 7, 8, 9, 10, J, Q, K, A in suits ♠, ♥, ♦, ♣
- 8 tricks per round, 8 cards per player

**Card objects:** Have `.rank` (str) and `.suit` (str, one of "♠","♥","♦","♣")

**Modes & Rank Order:**
- SUN (no trump): 7 < 8 < 9 < J < Q < K < 10 < A
- HOKUM (trump suit): 7 < 8 < Q < K < 10 < A < 9 < J

**Point Values:**
- SUN: A=11, 10=10, K=4, Q=3, J=2, rest=0
- HOKUM: J=20, 9=14, A=11, 10=10, K=4, Q=3, rest=0

**Positions:** "Bottom", "Right", "Top", "Left"
**Teams:** Bottom+Top (team 0) vs Right+Left (team 1)

**trick_history format** (from game state):
```python
[
    {
        "leader": "Right",
        "cards": [
            {"card": {"rank": "J", "suit": "♥"}, "playedBy": "Right"},
            {"card": {"rank": "7", "suit": "♥"}, "playedBy": "Top"},
            {"card": {"rank": "A", "suit": "♥"}, "playedBy": "Left"},
            {"card": {"rank": "8", "suit": "♥"}, "playedBy": "Bottom"},
        ],
        "winner": "Right"
    },
]
```

**Global Rules for ALL modules:**
- Pure functions only — no classes
- No external imports beyond `from __future__ import annotations` and `collections`
- Include module-level docstring and function docstrings
- Handle edge cases: empty inputs, missing dict keys, None values
"""

def extract_task_number(path):
    """Extract numeric task number for sorting."""
    match = re.search(r"task_(\d+)", os.path.basename(path))
    return int(match.group(1)) if match else 999

def main():
    # Parse optional --range argument (e.g. --range 13-16)
    task_range = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--range" and i < len(sys.argv):
            task_range = parse_range(sys.argv[i + 1])
        elif arg.startswith("--range="):
            task_range = parse_range(arg.split("=")[1])

    tasks = sorted(glob.glob(TASK_GLOB), key=extract_task_number)

    # Filter by range if specified
    if task_range:
        lo, hi = task_range
        tasks = [t for t in tasks if lo <= extract_task_number(t) <= hi]

    if not tasks:
        print("No task_*.md files found matching criteria!")
        return

    parts = [HEADER]
    for path in tasks:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        basename = os.path.basename(path)
        parts.append(f"\n---TASK--- ({basename})\n\n{content}")

    final = "\n".join(parts)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(final)

    range_str = f" (range {task_range[0]}-{task_range[1]})" if task_range else ""
    print(f"✅ Built batch prompt: {OUTPUT}{range_str}")
    print(f"   {len(tasks)} tasks included:")
    for t in tasks:
        print(f"   - {os.path.basename(t)}")
    print(f"\n   Total size: {len(final):,} chars")
    print(f"   → Open {OUTPUT}, Ctrl+A, Ctrl+C, paste into Claude Opus")

if __name__ == "__main__":
    main()
