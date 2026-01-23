---
name: BotLab
description: Tools to isolate, query, and test the Bot Algorithm without running a full game.
---

# BotLab Skill

This skill allows you to "interview" the bot. You can feed it a specific game state (hand, table cards, scores) and ask it what it would play and WHY. This is crucial for debugging "weird moves" reported by the user.

## Tools

### 1. Ask Bot
**Script**: `scripts/ask_bot.py`
**Usage**:
```bash
python .agent/skills/bot_lab/scripts/ask_bot.py --state my_state.json
```
**Options**:
- `--state <path>`: Path to a JSON file containing the `game_state`.
- `--player <index>`: (Optional) Override which player index to simulate (0-3).

**Input Format (JSON)**:
The `game_state` JSON should match the structure used in `bot_agent.py`.
Minimal example:
```json
{
  "phase": "PLAYING",
  "gameMode": "SUN",
  "trumpSuit": null,
  "players": [
    { "index": 0, "hand": [{"rank": "A", "suit": "♠"}, {"rank": "K", "suit": "♥"}], "position": "Bottom" }
  ],
  "tableCards": [],
  "playedCards": [],
  "currentRoundTricks": []
}
```

**Output**:
- **Action**: PLAY / BID / PASS
- **Card**: The card chosen (if PLAY)
- **Reasoning**: The internal logic string from the bot (e.g., "Leading Master Card").

## Workflow

1.  **Context**: You suspect the bot is calculating "Sun Strength" incorrectly.
2.  **Action**: Create a file `test_sun_hand.json` with a specific hand.
3.  **Command**: `python .agent/skills/bot_lab/scripts/ask_bot.py --state test_sun_hand.json`
4.  **Result**: The bot outputs its decision. You can iterate on the code in `bot_agent.py` and re-run this command instantly to verify the fix.
