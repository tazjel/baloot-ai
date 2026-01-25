# The Brain: Offline Learning Implementation 🧠

I have successfully implemented "The Brain", a system that allows your bots to learn from their mistakes.

## 🏗️ Architecture
1.  **AI Scout** (`scout.py`): Analyzes logs and identifies mistakes, saving them to `mistakes_manual.json`.
2.  **Trainer** (`train_brain.py`): Reads mistakes and saves the **Correct Move** to Redis (`brain:correct:{hash}`).
3.  **Bot Agent** (`bot_agent.py`): checks Redis before every move. If a learned situation is recognized, it **overrides** its default logic with the correct move.

## 🛠️ Key Fixes
- **Redis Key Mismatch**: Fixed `train_brain.py` to write keys matching `bot_agent.py`'s lookup pattern.
- **Card Index Mapping**: Updated `bot_agent.py` to translate the "Concept" of a move (Ace of Spades) into the specific "Card Index" (e.g., Index 1) required by the game engine.
- **Offline Logic Verification**: Created `ai_worker/mock_redis.py` to verify the logic even if Docker/Redis is offline.

## ✅ Verification
Ran `python scripts/verify_brain_pipeline.py`:
- **Scenario**: Bot holds [7-S, A-S]. Heuristic plays 7-S. Brain says "Play A-S".
- **Result**: `✅ VERIFICATION PASSED! Bot used the learned move.`

## 🚀 How to Use
1.  **Generate Data**: `python scripts/scout.py` (when you have game logs).
2.  **Train**: `python scripts/train_brain.py --file candidates/mistakes.json`.
3.  **Play**: Bots automatically use the Brain during gameplay if Redis is running.

## 🗣️ Voice & Trash Talk
I have polished the UI to include a dynamic Dialogue System where bots react to the game in Arabic.

### How it Works
1.  **Trigger**: Logic in `socket_handler.py` detects key game events (Playing a card, Bidding).
2.  **Generation**: The `DialogueSystem` uses `gemini-flash-latest` to generate a short, personality-based reaction (Trash Talk or Complaint).
    - **Khalid (Aggressive)**: "سرا!" (Get out!)
    - **Saad (Balanced)**: "وش ذا اللعب؟" (What is this play?)
    - **Abu Fahad (Conservative)**: "يا ساتر" (Oh protector)
3.  **Delivery**:
    - **Visual**: A `SpeechBubble` appears on the player's avatar in the frontend.
    - **Audio**: The browser's native Text-to-Speech (`window.speechSynthesis`) speaks the Arabic text with pitch/speed adjustments per character.

### Verification
- Ran `scripts/test_dialogue.py` which successfully generated Arabic banter using the AI model interactively.
- Confirmed `socket` events emit correctly to the frontend.
