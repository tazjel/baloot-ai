# Baloot Rules & Mechanics

This document outlines the Baloot rules implemented in the project, verified against the codebase and user requirements.

## 1. Bidding Phase
The bidding engine supports a two-round bidding system with complex interrupt mechanics.

### Round 1 & 2
- **Round 1**: Players can bid **Hokum** (only matching the floor card's suit) or **Sun** (no suit).
- **Round 2**: If everyone passes in Round 1, Round 2 begins. Players can bid **Hokum** (any suit *except* the floor card's suit) or **Sun**.
- **Pass**: If all players pass in Round 2, the hand is redealt, and the dealer rotates.

### Special Calls
- **Ashkal (Sun)**: A special "Sun" bid made **only by the Dealer** or the **Dealer's Left Opponent** (Prio 3 or 2) during **Round 1 or Round 2**. 
    - It acts as a Sun contract for the *partner* but is called "Ashkal".
    - **Constraint**: Cannot call Ashkal if the floor card is an Ace.
    - **Effect**: The Partner becomes the Bidder and takes the floor card (if Round 1).
    - **Strategy**: Usually a signal that the caller dislikes the floor suit. Partner is advised to play the **opposite color** of the floor card (in Round 2) or **Start with Different Suit of Same Color** (in Round 1).
- **Kawesh**: A player can request a redeal if their hand contains no "Court Cards" (A, K, Q, J, 10) - i.e., only 7, 8, 9.
    - *Pre-Bid*: Redeal, Dealer Retained.
    - *Post-Bid*: Redeal, **Dealer Rotation**.
- **Gablak (Sun Hijack)**: "Sun" is significantly higher than "Hokum".
    - **Any player** can interrupt a Hokum bid by bidding Sun.
    - If a player with higher priority (closer to Dealer's right) bids Sun, they take it. If a lower priority player bids Sun, a "Gablak Window" opens for higher priority players to reclaim it.

### Doubling Chain
Once a contract is finalized, the **Doubling Phase** begins:
1.  **Double (Dobl)**: Opponents can double the score (x2).
2.  **Triple (Khamsin)**: The bidding team can reply with Triple (x3).
3.  **Four (Raba'a)**: Opponents can reply with Four (x4).
4.  **Gahwa (Coffee)**: The bidding team can reply with Gahwa, which instantly wins the match if successful.

- **Sun Firewall**: Players can only Double a **Sun** contract if:
    - Their team's score < 100
    - The opponent's score > 100
- **Hokum Variants**: If a Hokum contract is Doubled, the bidder must choose the variant:
    - **OPEN**: Standard play.
    - **CLOSED (Magfool)**: Specific restriction: If a player has *any* non-trump card, they *cannot* lead a Trump card as their first play (unless they only have Trumps).

## 2. Play Phase
- **Game Modes**:
    - **Sun**: No Trumps. Suit must be followed. Scoring is based on Rank (A>10>K>Q>J>9>8>7).
    - **Hokum**: Trumps exist. Suit must be followed. If void in suit, *must* play Trump (if available). If opponent played Trump, *must* Over-Trump (if possible).
- **Play Order**: Rotates counter-clockwise. Trick winner leads next.
- **Magfool Constraint**: In Closed Doubled Hokum, players cannot lead generic Trumps if they hold non-trump cards.

## 3. Projects (Mashaari) & Bonuses
Projects are declared during **Trick 1**.

### Types
- **Sira** (Sequence of 3): 20 Abnat (4H/2S pts).
- **Fifty** (Sequence of 4): 50 Abnat (10H/5S pts).
- **Hundred** (Sequence of 5): 100 Abnat (20H/10S pts).
- **Hundred** (4 of a Kind: K, Q, J, 10): 100 Abnat.
- **400** (4 Aces in Sun): 200 Abnat (40 Sun pts).
- **Baloot**: King + Queen of Trump suit (Hokum only). Worth 20 Abnat.

### Rules
- **Hierarchy**: 400 > 100 (Seq/4Kind) > 50 > Sira.
- **Comparison**: Rank (A > K > Q...) determines winner between same types.
- **Winner Takes All**: The team with the strongest project scores *all* their projects. The losing team scores *none* (exception: Baloot is always scored).

## 4. Special Mechanics
- **Akka (Hokum)**: A player can claim "Akka" if they hold the highest remaining card in a non-trump suit.
    - *Constraints*: Hokum only, Non-Trump suit, Card cannot be an Ace.
- **Sawa**: A player claims they can win *all* remaining tricks.
    - *Refusal*: Opponents can refuse *only* if they hold a "Master Card" (Guaranteed Winner) in any suit.
    - *Acceptance*: If accepted, round ends immediately, claimer takes remaining points.
    - *Bot Logic*: Bot will Refuse if it holds any Master Card (Ace in Sun, or highest remaining Trump in Hokum). Otherwise, it Accepts.
- **Kaboot**: Winning *all* tricks in a round.
    - **Sun**: Worth 44 points total (instead of 26).
    - **Hokum**: Worth 25 points total (instead of 16).

## 5. Scoring
- **Abnat (Raw Points)**: Calculated based on cards won.
    - **Sun**: A=11, 10=10, K=4, Q=3, J=2. Total 130 + 130(Projects) + 10(Last Trick).
    - **Hokum**: J(Trump)=20, 9(Trump)=14. A=11, 10=10, K=4, Q=3.
- **Game Points (Final Score)**:
    - **Sun**: Abnat / 5 (roughly). Total round = 26 points.
    - **Hokum**: Abnat / 10. Total round = 16 points.
- **Rounding**: Score rounding (e.g., remainder > 5 rounds up).
- **Khasara**: If the Bidding team scores *less* than the Opponent team, they lose *all* their points to the Opponent (Total Pot Transfer).
- **Winning Score**: First team to reach **152** points wins the game.
- **Winning Score**: First team to reach **152** points wins the game.

## 6. Penalties & Human Mistakes (Qayd)

The game implements a strict "Card Laid is Card Played" rule with potential for fouls (Revoke).

### Freedom of Play
- Players are **not** blocked from making illegal moves (e.g., failing to follow suit, under-trumping).
- The onus is on the player to know the rules and play correctly.

### Qayd (Penalty) System
- If a player commits a foul (illegal move), the game **does not stop automatically**.
- Opponents (Human or AI) must detect the foul and click the **"Qaydha" button** (Gavel Icon).
- **Qayd Resolution**:
    1.  **Valid Claim**: If the move was indeed illegal, the **Offending Team LOSES** the round immediately (Full points awarded to opposition: 16 in Hokum, 26 in Sun).
    2.  **False Claim**: If the move was legal, the **Reporting Team LOSES** the round immediately for the disruption.
- **Strict Enforcement**: AI Bots are trained to detect fouls instantly. **Do not try to cheat them.**
