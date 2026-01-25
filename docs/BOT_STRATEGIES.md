# Bot Strategy Guide

strategies and heuristics for the AI Bot.

## Bidding Strategies

### Ashkal Signal
- **Trigger**: When your partner calls **Ashkal** (Sun for Partner).
- **Meaning**: This is a strong signal that the partner **dislikes** the suit of the Floor Card.
- **Response**:
    - **Round 1 (Floor Match)**: Partner wants you to play the **SAME Color** but different suit.
        - *Example*: Floor is **Hearts** (Red) -> Play **Diamonds** (Red).
    - **Round 2 (Floor Mismatch)**: Partner wants you to play the **OPPOSITE Color**.
        - *Example*: Floor is **Hearts** (Red) -> Play **Spades** or **Clubs** (Black).

### Strong Project Ashkal
- **Condition**: If you hold a very strong project (4 Aces, 4 Tens, 4 Queens, etc.).
- **Action**: Call **Ashkal**.
- **Reasoning**: Secures the bid and maximizes the value of your high-scoring project (400 or 100), with the hope of receiving better playing cards from the partner's hand or the redeal/floor.

## Playing Strategies

### General
- Prioritize playing high cards in Sun if partner is winning, to save them or maximize points.
- In Hokum, do not lead Trump unless necessary or trying to draw trumps.

## The Hybrid AI Mind

### 1. The Reflex (Heuristic)
The bot uses standard rules (e.g., "Always cover a King with an Ace") for 90% of moves. This is fast and reliable.

### 2. The Brain (Redis Memory)
Before acting, the bot checks Redis. If "The Scout" has previously analyzed this specific situation and found a mistake, the bot uses the **Learned Correction**.
- **Key**: `brain:correct:{context_hash}`
- **Source**: Gemini AI Analysis of past games.

### 3. Personalities (Voice & Trash Talk)
Bots have distinct personalities that affect their bidding and speech:
- **Saad (Balanced)**: Standard risk. Says "Thinking..." or neutral comments.
- **Khalid (Aggressive)**: Bids risky Sun/Hokum. Says "Sira!" (Get out!) or taunts.
- **Abu Fahad (Conservative)**: Rarely bids unless holding masters. complains "Ya Sater" (Oh protector).
