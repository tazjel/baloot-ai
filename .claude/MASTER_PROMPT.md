# Baloot AI — Batch Module Generation

You are generating Python modules for a Baloot AI strategy system.

## Instructions
Below are multiple task specifications separated by `---TASK---` markers. For EACH task:
1. Read the specification carefully
2. Write the complete Python module
3. Output it in a fenced code block labeled with the filename

**Output format** — for each task, produce EXACTLY this:

```
### [filename]
```python
# complete module code here
```

Process ALL tasks below. Do NOT stop after one. If you hit limits, finish the current module completely before stopping.

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
- Include module-level docstring
- Include function docstrings
- Handle edge cases: empty inputs, missing dict keys, None values

---TASK---

[PASTE CONTENTS OF task_13_opponent_model.md HERE]

---TASK---

[PASTE CONTENTS OF task_14_hand_shape.md HERE]

---TASK---

[PASTE CONTENTS OF task_15_trick_review.md HERE]

---TASK---

[PASTE CONTENTS OF task_16_cooperative_play.md HERE]
