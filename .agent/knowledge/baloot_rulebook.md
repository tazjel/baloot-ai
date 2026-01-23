# Baloot Game Workflow & Specifications

**Source:** User provided research based on "ExternalApp" application.

### **1. Session Initialization and Environment Setup**

The game begins by establishing the virtual environment, referred to as the "Majlis."

* **Board Layout:** The application renders a square playing surface covered in a traditional Sadu-patterned carpet.
* **Player Positioning:** Four players are seated at cardinal points. The local user is always positioned at the South (bottom) of the screen. The user's partner is seated directly opposite at North (top), while opponents occupy the East (right) and West (left) positions.
* **Dealer Selection:** A "D" marker icon is assigned to one player to designate the dealer. This marker moves counter-clockwise after every completed round to shift the dealing responsibility.
* **Scoreboard:** A score panel initializes at the top of the screen (or side for desktop), displaying two main columns: "Lana" (Us) and "Laham" (Them), both starting at zero.

### **2. Phase I: The Initial Distribution (The Deal)**

The workflow enters the first active state where the system mimics the physical dealing of cards.

* **Animation:** The system distributes the first batch of cards. Animations show cards flying from the center deck to each player's position.
* **Card Count:** Each player receives exactly five cards. These are dealt face-down to opponents and face-up to the user.
* **The "Buyer" (Public Card):** A single card is revealed face-up in the exact center of the playing board. This card determines the initial suit for the bidding phase.
* **Interaction State:** At this stage, players can view their five cards but cannot yet play them. The interface locks card interaction and highlights the "Buyer" card.

### **3. Phase II: The Bidding Workflow (The Buy)**

The Bidding Phase is a strict state machine that interrupts the dealing process. It determines the **Contract** (Sun or Hokum), the **Trump Suit**, and the **Buyer** (who takes the public card).

#### **Step 1: The Public Card (The Buyer) Display**

* After dealing 5 cards to each player, the system must pause.
* The 21st card (The Public Card) is revealed face-up in the center of the board.
* **System Logic:** The system must identify the suit and rank of this card (e.g., "Ace of Hearts"). This card sets the "First Round" suit.

#### **Step 2: First Bidding Cycle (First Dora)**

The bidding starts with the player to the **right** of the Dealer and moves **counter-clockwise**.

* **Player Options:**
1. **Hokum (Hukm):** Buying the card to play a Trump game. The trump suit *must* be the same suit as the Public Card.
2. **Sun (San):** Buying the card to play a No-Trump game.
3. **Pass (Bass):** Declining to buy.
4. **Ashkal:** (See specific logic below).


* **The "Sun" Priority Rule (Critical Logic):**
* "Sun" is strictly stronger than "Hokum".
* If Player 1 bids "Hokum", the bidding does **not** end. The turn passes to Player 2.
* If Player 2 (or 3 or 4) bids "Sun", this bid **overrides** Player 1's "Hokum".
* **Strict Priority Constraint:** If a player bids "Sun", the system must check if any player with **higher priority** (who previously passed or bid Hokum) wants to challenge it. *However, in most digital implementations like ExternalApp, the "First Sun" secures the bid immediately to speed up play, unless a "Strict Priority" mode is active.*
* **Recommendation for Antigravity:** Implement "First Valid Sun Wins" for smoother UX, as retroactively asking Player 1 disrupts flow.


* **The "Ashkal" Logic (Conditional Button):**
* **Eligibility:** The "Ashkal" button must **only** appear for the **3rd player** (Dealer's teammate) and the **4th player** (Dealer). Players 1 and 2 cannot call Ashkal.
* **Function:** Calling "Ashkal" buys the card as **Sun**, but the card is given to the **Partner**, not the caller.
* **The Ace Constraint:** The system must **disable** the Ashkal button if the Public Card is an **Ace**. Ashkal is illegal on an Ace. If a user tries to call it, the system must force a regular "Sun" bid for the caller instead.



#### **Step 3: Second Bidding Cycle (Second Dora)**

If all four players choose "Pass" in the First Cycle, the Second Cycle begins immediately.

* **State Change:** The Public Card remains on the table, but it is no longer binding for the suit.
* **Player Options:**
1. **Hokum (Pick a Suit):** Players can buy the card as Hokum but **must choose a different suit** than the Public Card.
* *UI Logic:* When clicking "Hokum", a popup selector appears with the 3 other suits. The Public Card's suit is greyed out.


2. **Sun:** Players can still buy as Sun.
3. **Pass:** Decline.


* **Second Round Priority:**
* "Sun" still overpowers "Hokum".
* **No Ashkal:** The "Ashkal" option is **removed** in the Second Cycle. Even the Dealer cannot call it.



#### **Step 4: The "Kawesh" (Reshuffle) Check**

This is a rare but vital rule for fairness.

* **Trigger:** If a player is dealt a hand with **zero points** (only 7s, 8s, and 9s that do not match the trump suit options), they can request a "Kawesh".
* **System Logic:** If the bidding ends with no buyer (all Pass in Round 2), the cards are collected and redealt by the next dealer.
* **Player Trigger:** If a player has a zero-point hand, they may have a "Reshuffle" button active during their turn, usually forcing a restart of the round.

#### **Step 5: Bidding Conclusion & Distribution**

Once a bid is confirmed:

1. **Card Transfer:** The Public Card moves from the center to the **Buyer's** hand (or the Partner's hand if "Ashkal" was used).
2. **Final Deal:** The system deals the remaining cards from the deck.
* **The Buyer:** Receives **2** cards (Total 8).
* **Others:** Receive **3** cards (Total 8).


3. **Doubling Phase (The Dabal):** Before the first trick is played, the system opens a brief window for the opposing team to click **"Double"** (multiply score x2). If doubled, the buying team can reply **"Triple"** (x3), and so on.

### **Summary of Logic Gates for Developers**

1. **Is Card Ace?** -> If YES, Disable Ashkal.
2. **Is Round 2?** -> If YES, Disable Ashkal; Disable "Hokum" for Public Card Suit.
3. **Did Player Bid Sun?** -> If YES, End Bidding (Contract = Sun, Buyer = Current Player).
4. **Did Player Bid Hokum?** -> Check next players. If next player bids Sun, Sun wins. If all pass, Hokum wins.

### **4. Phase III: Contract Finalization and Full Deal**

Once a player buys the contract, the distribution phase concludes.

* **Taking the Buyer:** The player who bought the contract (or the dealer in the case of Ashkal) takes the Public Card from the center into their hand.
* **Secondary Distribution:** The system deals the remaining cards. The buyer receives two additional hidden cards, while all other players receive three additional hidden cards.
* **Hand Sorting:** The user now holds 8 cards. The system automatically sorts these cards. In a "Sun" contract, they are typically sorted A-K-Q-J-10. In a "Hokum" contract, the Trump suit is moved to the left or highlighted, and the rank order changes to J-9-A-10.

### **5. Phase IV: Project Declaration (Mashrou')**

Before the combat begins, players must announce any special combinations they hold.

* **Detection:** The system scans the user's hand for patterns: "Sira" (sequence of 3), "Fifty" (sequence of 4), "Hundred" (sequence of 5 or 4 heads), or "400" (4 Aces in Sun).
* **Announcement Trigger:** When the first trick begins, players with valid projects see a "Declare" button.
* **Visual Indicator:** Upon declaration, a badge or text bubble (e.g., "Sira") appears next to the player's avatar.
* **Resolution Logic:** The system compares the projects of opposing teams. The team with the highest-ranking project scores points for *all* their projects, while the opposing team scores zero for theirs. The winning project is then visually revealed to all players for verification.

### **6. Phase V: The Play (Trick-Taking)**

This is the core loop of the game, repeated 8 times per round.

* **Leading:** The player to the right of the dealer throws the first card.
* **Card Throw Animation:** When a user swipes a card up or taps it, the card animates along a curve (Bezier path) from their hand to the center of the "carpet."
* **Constraint Logic (Follow Suit):** The system enforces rules. If the lead card is Hearts, the user's non-Heart cards are dimmed or disabled. If the game is Hokum and the user has no suit, the system highlights the Trump cards to indicate they must "Cut."
* **Trick Collection:** Once four cards are played, the system determines the winner based on the contract rules. The four cards are then swept rapidly towards the winning team's side (Lana or Laham) to symbolize capturing the trick.
* **Last Trick Bonus:** The system internally flags the winner of the 8th and final trick to award the 10-point bonus.

### **7. Phase VI: Special Functions (Sawa & Qayd)**

During the Play Phase, specific interruption events can occur.

* **Sawa (Claim):** A player who believes they can win all remaining tricks presses the "Sawa" button. Their cards are revealed face-up. Opponents are given a choice to "Accept" or "Refuse". If accepted, the round ends instantly, and points are awarded. If refused, play continues with the claimant's hand exposed.
* **Qayd (Penalty):** If a player makes a mistake (like playing the wrong suit in real life, though the app prevents this, or making a false Sawa claim), the "Qayd" logic triggers. A visual "X" or red flag appears. The offending team's score for the current round is reset to zero, and the opposing team is awarded the full potential score of the round.

### **8. Phase VII: Scoring and Round Conclusion**

After the 8th trick is collected, the calculation screen appears.

* **Point Summation:** The system counts the card values captured by each team (Abnat).
* **Rounding:** The raw score is rounded to the nearest ten (e.g., 25 becomes 30 in some rules, or 20 in others).
* **Conversion:** The rounded score is divided by 10. In Sun, this figure is multiplied by 2.
* **Project Addition:** Any points from declared projects (Sira, 50, etc.) are added to the final total.
* **Scoreboard Update:** The main "Lana/Laham" scoreboard updates with the new total.
* **Win Condition Check:** The system checks if either team has reached 152 points. If so, the game ends, and the victory screen is displayed. If not, the "D" marker moves to the next player, and the workflow resets to Phase I.

---

## Technical Specifications & Assets (ExternalApp Style)

### **1. Card Asset Specifications (Artistic & Technical)**

To achieve the crisp readability seen in *ExternalApp*, your card assets must balance traditional aesthetics with digital utility.

#### **A. Dimensions and Resolution**
* **Aspect Ratio:** **5:7** (approx. 1:1.4). This is slightly wider than a standard Bridge card (2.25" x 3.5"), which is critical for mobile. The wider format allows for larger indices (numbers) that remain legible even when cards are overlapped tightly in a hand of 8.
* **Source Resolution:** Design at **750px × 1050px** (300 PPI). This allows downscaling for mobile without losing edge sharpness on Retina/OLED screens.
* **Render Size (Mobile):** On screen, cards should dynamicall scale but generally render around **140px width** on standard phones to ensure touch targets are accessible.

#### **B. Visual Style & Iconography**
* **Indices (The most important part):**
    * **Position:** Strictly **Top-Left** and **Bottom-Right**.
    * **Size:** The index (e.g., "A♠") must occupy **30-35%** of the card’s width.
    * **Dual Language:** *ExternalApp* supports both **Arabic (أ, ك, ب, و)** and **English (A, K, Q, J)** indices. For Antigravity, implementing a toggle in settings for "Card Language" is a high-value feature.
    * **Font:** Use a bold **Slab-Serif** font (like *Roboto Slab* or *Courier New* bold). Avoid thin fonts; they disappear against the busy game board.
* **Court Cards (Face Cards):**
    * **Cultural Localization:** While standard French designs are acceptable, *ExternalApp* utilizes localized art where Kings and Jacks wear the **Ghutra/Shemagh** (traditional Saudi headwear). This greatly enhances the "Majlis" atmosphere.
    * **Contrast:** Reduce the opacity of the face card artwork by 10-15% or place the Index on a solid white background patch to ensure the artwork doesn't clash with the number.

### **2. The "Hand" Layout Logic (CSS & JS Architecture)**

In Baloot, a player holds 8 cards. Displaying these on a narrow mobile portrait screen requires a **Radial Fan Algorithm**. You cannot use a simple horizontal list (`display: flex`).

#### **A. The Radial Fan Formula**
To recreate the *ExternalApp* curved hand:
1. **Pivot Point:** Imagine an invisible anchor point located **off-screen**, roughly **50% of screen height** below the bottom of the screen, centered horizontally.
2. **Card Rotation:**
    * Total Fan Angle: ~60 degrees.
    * Step Angle: `TotalAngle / (NumCards - 1)`.
    * Card `i` rotation: `StartAngle + (i * StepAngle)`.
3. **Position Calculation (JS/Unity):**
    * `x = PivotX + Radius * sin(angle)`
    * `y = PivotY - Radius * cos(angle)` (This drops the side cards lower than the center cards).

#### **B. Z-Index and Layering (Crucial)**
* **Order:** Cards must be rendered from **Left to Right** in the DOM/Hierarchy.
    * Card 1 (Leftmost): `z-index: 1`
    * Card 8 (Rightmost): `z-index: 8`
* **Why?** In standard card indices, the number is on the top-left. If you layer Right-to-Left, the right card will cover the number of the left card, making the hand unreadable.

#### **C. Selection State (Active Interaction)**
When a user taps a card, it must visually "pop" to confirm selection before playing.
* **CSS Transformation:** `transform: translateY(-30px) scale(1.1);`
* **Z-Index:** `z-index: 100;` (Moves to front of stack)
* **Shadow:** `box-shadow: 0px 10px 20px rgba(0,0,0,0.5);`
* **Logic:** The system must listen for a "Play" command (swipe up or double tap). If the card is merely tapped once, it stays in this "Selected" state.

### **3. Animation Systems**

Animations in *ExternalApp* are not just cosmetic; they mask network latency and clarify game state.

#### **A. The "Deal" Sequence**
* **Source:** All cards spawn from the center of the table (The Deck).
* **Timing:** They do not appear instantly. Use a **Staggered Delay** of 0.05s per card.
* **Trajectory:** Cards should travel on a straight line to the player's hand, but **flip** (scale X from 1 -> 0 -> 1) halfway through to reveal the face.

#### **B. The "Throw" (Play Card)**
When a player plays a card:
* **Path:** Use a **Cubic Bezier Curve**, not a straight line. The card should arc slightly "up" into the air before landing on the table.
* **Rotation:** Add a random rotation jitter (`Math.random() * 20 - 10` degrees) upon landing. This makes the pile look natural and organic, like a real messy table, rather than a perfect computer stack.
* **Scale:** The card should scale down to **~60-70%** of its hand size when it hits the table to create a sense of depth/perspective.

#### **C. "Sawa" and Project Visuals**
* **Project Declaration:** If a player declares "Sira" or "50", a bubble notification appears attached to their avatar. Simultaneously, the specific cards involved in the project should briefly **glow gold** or pulse in their hand to confirm to the player which cards are being declared.
* **Winning the Trick:** When a round finishes (4 cards played), the cards shouldn't just vanish. They must **sweep** rapidly towards the winning player's score pile (e.g., if North wins, cards fly North). This is a vital visual cue for tracking who is winning.

---

## Detailed Design & Scoring Logic

### **1. Interface Design and Asset Readability**

This section outlines the visual and spatial requirements, focusing on clarity, "glanceability," and minimizing cognitive load.

#### **1.2 Spatial Zoning and Hierarchy**
To prevent input errors and visual clutter, the screen is divided into three strict interaction zones. The design adapts for Mobile (Portrait) and Website (Landscape).

**A. Mobile Layout (Portrait Mode)**
Prioritizes single-handed play.
*   **Zone 1: Top HUD (15%):** Scoreboard (Center), Menu (Left), Social (Right).
*   **Zone 2: The Arena (35%):** The "Majlis" carpet. Opponent avatars seated at edges. Center is the "Drop Zone" for played cards.
*   **Zone 3: Dashboard (10%):** Action buttons (Pass, Double) and Timer appear here, above the hand.
*   **Zone 4: Player Hand (40%):** Docked at bottom. Cards fan on a convex curve (Anchor point 50% off-screen).

**B. Website Layout (Landscape Mode)**
Utilizes extra width for information density.
*   **Grid:** 25% Sidebar (Left/Right) for Chat/Logs vs 75% Game Table.
*   **Sidebar:** Persistent Chat Room, Game Log (History), and System Menu.
*   **Table:** Central square board. "Negative space" around the table uses thematic background (e.g., blurred tent interior).
*   **Interaction:** Hover-to-select (Mouse) instead of tap-to-select.

**C. Common Interaction Logic**
1.  **Hand Interaction:**
    *   **Card Fanning:** Cards must fan dynamically. The fan expands when touched.
    *   **Input Logic:** A "Lift-to-Select" mechanism is recommended. Tapping a card once lifts it 20px (Selection State); tapping it again or swiping up plays it (Action State).
2.  **Arena (Center):**
    *   **Trick Stacking:** Played cards are placed in the center but offset slightly toward the player who played them.
    *   **Public Card:** During bidding, the 21st card ("The Buyer") is displayed prominently in the center with a **pulsing Gold Border**.
3.  **Periphery (HUD):**
    *   **Timers:** A radial countdown timer wraps around the active player's avatar.
    *   **Scoreboard:** Collapsible HUD (Mobile) or Persistent (Web) displaying "Lana" vs "Laham".

#### **1.3 Card Design and Accessibility**
Cards are the primary interface element. Their design prioritizes readability on small screens over artistic flair.
*   **Color Coding:**
    *   **Standard:** Black (Spades/Clubs), Red (Hearts/Diamonds).
    *   **Accessibility Mode:** An option to enable a 4-color deck (e.g., Blue Diamonds, Green Clubs) to assist color-blind players.
*   **State Visualization:**
    *   **Active:** 100% Opacity.
    *   **Disabled:** 50% Opacity + Grayscale. This state is applied automatically to cards that cannot be legally played (e.g., non-trump cards when a trump is required).

#### **1.4 Visual Feedback and "Juice"**
"Juice" refers to visual cues that reinforce game actions.
*   **Dealing Animation:** Cards are dealt one by one from the center deck to players, mimicking the physical rhythm of a deal.
*   **Project Badges:** When a player declares a project (e.g., "Sira" or "400"), a badge icon appears briefly over their avatar to notify opponents.
*   **Trick Collection:** Winning cards sweep rapidly toward the winner’s score pile to reinforce the accumulation of points ("Abnat").

### **2. Scoring System and Mathematical Logic**

The application must implement the Baloot specific scoring algorithms for "Abnat" (Card Points) and "Projects" (Melds).

#### **3.1 Card Point Values (Abnat)**
The scoring engine must switch values based on the contract type.

| Card Rank | Sun (San) Value | Hokum (Trump) Value | Hokum (Non-Trump) Value |
| :--- | :--- | :--- | :--- |
| **Ace (A)** | 11 | 11 | 11 |
| **Ten (10)** | 10 | 10 | 10 |
| **King (K)** | 4 | 4 | 4 |
| **Queen (Q)** | 3 | 3 | 3 |
| **Jack (J)** | 2 | 20 | 2 |
| **Nine (9)** | 0 | 14 | 0 |
| **8 / 7** | 0 | 0 | 0 |

#### **3.2 Round Scoring Formula**
At the end of a round, the system calculates the raw score and converts it.

*   **Sun Calculation:**
    *   Total Raw Points: 130.
    *   Equation: `Score = Round(Raw Points / 10) * 2`
    *   Example: 45 raw points -> 5 -> 10 game points.
    *   Max Score: 26 points.
*   **Hokum Calculation:**
    *   Total Raw Points: 152.
    *   Equation: `Score = Round(Raw Points / 10)`
    *   Example: 45 raw points -> 5 game points.
    *   Max Score: 16 points.
*   **Project Bonuses:** Added to the final score *after* the rounding calculation.
    *   **Sira** (Sequence of 3): +4 (Sun) / +2 (Hokum)
    *   **50** (Sequence of 4): +10 (Sun) / +5 (Hokum)
    *   **100** (Sequence of 5): +20 (Sun) / +10 (Hokum)
    *   **100** (4 of a Kind): +20 (Sun) / +10 (Hokum)
    *   **400** (4 Aces in Sun): +40.

#### **3.3 Multipliers (Doubling System)**
*   **Double (x2):** Called by defenders.
*   **Triple (x3):** Called by buyers.
*   **Four (x4):** Called by defenders.
*   **Gahwa:** Automatic win (152 points).
*   **Logic:** Multipliers apply to the final game score of the round. Projects are also multiplied (except "Baloot" project).

### **3. Functions: Sawa, Qayd, and Dispute Systems**

#### **4.1 The "Sawa" Function (Claim Win)**
The Sawa feature allows a player to claim all remaining tricks without playing them out.
*   **Trigger:** A "Sawa" button becomes active during the player's turn.
*   **Resolution:**
    *   **Accept:** The round ends immediately. The claimant's team is awarded all remaining card points + 10 points (Last Trick bonus).
    *   **Challenge:** The game continues with the claimant's cards exposed.
    *   **Success Condition:** If the claimant wins every remaining trick, the claim is valid.
    *   **Failure Condition:** If the claimant loses even one trick, the claim fails, triggering a Qayd (Penalty).

#### **4.2 The "Qayd" (Penalty) Function**
The Qayd is a system function used to penalize rule violations.
*   **Triggers:**
    *   **False Sawa:** Claiming Sawa but failing to win all tricks.
    *   **Revoke (Renounce):** Not following suit when able (prevented by UI constraints in digital play).
    *   **Hokum Violation:** Playing a non-trump card when holding a trump (if the lead was a trump and the player has trumps).
*   **Scoring Consequence:**
    *   **Offending Team:** Score resets to 0 for the current round.
    *   **Opposing Team:** Awarded the full possible score for the round (26 for Sun, 16 for Hokum) plus any declared projects.

#### **4.3 Illegal Move Prevention (System Logic)**
To minimize disputes, the application logic enforces rules proactively:
*   **Suit Constraints:** If the lead card is Hearts, the system disables interactions for all Spades, Diamonds, and Clubs in the user's hand, unless the user has no Hearts.
*   **Trump Constraints (Hokum):** If a Trump is led, the system enforces playing a higher Trump if available. If a non-Trump is led and the user cannot follow suit, the system highlights Trump cards if available (forcing the user to "Cut").
*   **Dispute System (Post-Game):** For logic that cannot be blocked (e.g., connection dropping), a "Report" function sends the game log to the server. If the server detects a pattern of disconnecting during losing hands ("Escape"), the player receives a temporary matchmaking ban.

---

## Technical Audit & Implementation Guidelines

This section deconstructs the specific implementation details required to match the "ExternalApp" desktop experience.

### **1. Virtual Environment & Physics**

*   **2.5D Perspective:** The game uses an orthographic/trapezoidal projection.
    *   *Implementation:* Active player view (South) is widest. Opponent positions (East/West) are foreshortened.
    *   *Card Scale:* Card assets must scale down by 30-40% as they move from the hand (South) to the center pit to simulate depth.
*   **Surface Friction:** The table simulates felt.
    *   *Physics:* Cards must not slide indefinitely. Implementation requires a high friction coefficient dampening effect. Using Cubic Ease-Out functions for throws is critical to match this.

### **2. Visual Workflows & State**

*   **Deal Animation:**
    *   *Origin:* Cards spawn from center.
    *   *Flip:* Cards scale X to 0 then back to 100% to simulate flipping face-up as they reach the user.
*   **Timer Synchronization:**
    *   *Logic:* Visual timers (green -> yellow -> red) must be synchronized via NTP or offset calculation to the server's authoritative clock to prevent "false active" states.
*   **Project Reveals:**
    *   *Overlay:* "Show Project" overlays must be semi-transparent (80-90% opacity) to ensure the active game board remains visible underneath.

### **3. Advanced Gameplay Features**

*   **"Sawa" (Fast-Forward):**
    *   *Logic:* If a player has a winning hand, a "Sawa?" button appears.
    *   *Visuals:* Bypasses standard turn timers and deals remaining cards rapidly (e.g., 100ms interval) to conclude the hand instantly.
*   **Challenge System (Restriction/Taqyeed):**
    *   *Visuals:* A global pause filter (sepia/dim) applies when a challenge is initiated.
    *   *History:* Players need a UI to scroll back through the "History Log" to identify the contested move.

### **4. Rendering Pipeline**

*   **Z-Sorting:**
    *   *Pit Logic:* Strictly time-based. Card $N+1$ always renders above Card $N$.
    *   *Hand Logic:* Left-to-Right layering (Card 0 is bottom Z-index, Card 7 is top) to ensure indices are visible.
*   **Golden Cards:**
    *   *Optimization:* Use pre-baked reflection maps for "shine" effects instead of real-time ray tracing to maintain performance on lower-end hardware.

### **5. Latency Masking (Rubber-banding)**

*   **Client-Side Prediction:**
    *   **Throw:** Animation starts immediately on click/swipe.
    *   **Correction:** If server invalidates the move (e.g., illegal suit), the card smoothly interpolates back to hand ("Rubber-banding") rather than teleporting.

### **6. Technical Implementation Checklist**

This table serves as a quick developer reference for "Antigravity" compliance.

| Feature Classification | Implementation Standard (ExternalApp) |
| :--- | :--- |
| **Card Aspect Ratio** | **5:7** (Wider than Bridge, narrower than Poker) |
| **Index Typography** | **Slab-Serif Bold** (Roboto Slab, Courier New) |
| **Hand Layout** | **Radial Arc** (Pivot point off-screen bottom, Y > Screen Height) |
| **Z-Index Layering** | **Left-to-Right** (i=0 is Bottom, i=7 is Top) |
| **Selection State** | `transform: translateY(-30px)` + `z-index: 100` |
| **Throw Animation** | **Cubic Bezier Curve** + Random Rotation Jitter on landing |
| **Responsiveness** | Hand width clamps to screen width; overlap density increases dynamically |
| **Thump Effect** | Scale 1.1x -> 1.0x on impact + Audio Cue |

---

## Detailed Project (Mashrou') Implementation Guide

This comprehensive guide details the **Project (Mashrou')** mechanics for the Antigravity application, focusing on the UI/UX timing, the mathematical hierarchy of claims, and the technical logic required to replicate the authentic *ExternalApp* experience.

### 1. The Declaration Phase: UI Timing and Interaction

In Baloot, projects are declared verbally in the first trick but "shown" (proved) in the second. In the digital application, this is split into **Declaration Buttons** and **Validation Logic**.

#### **A. When Buttons Appear (The Window of Opportunity)**

The system must run a `ScanHand()` function immediately after the deal is complete.

* **Trigger:** The buttons appear **only** when it is the **user's turn to play** during the **First Trick** (Round 1 of 8).
* **Condition:** The buttons are visible *only* if the `ScanHand()` detected valid combinations (Sira, 50, 100, 400).
* **Visual Location:** These buttons should float directly above the player's hand, distinct from the "Play Card" interaction area.

#### **B. When Buttons Disappear**

* **Action:** As soon as the user selects a project button (e.g., taps "Sira") OR plays a card on the table, the buttons must vanish immediately.
* **Timeout:** If the turn timer expires and the system auto-plays a card, the right to declare is forfeited, and buttons disappear.
* **Constraint:** You cannot declare a project *after* throwing the card for the first trick. The system must block the "Play Card" event if a project button is pressed, requiring a second confirmation, or treat the project click as a "Tag" that attaches metadata to the subsequent card throw.

---

### 2. The Logic Engine: Comparison and Team Priority

This is the most complex logic block. The server must collect all declarations from the four players during Trick 1, but **resolve** them before Trick 2.

#### **A. Hierarchy of Strength (The Comparator)**

The system compares the *highest* project held by Team A against the *highest* project held by Team B.

1. **400** (4 Aces - Sun Only) [Highest]
2. **100** (Sequence of 5 cards)
3. **100** (4 of a Kind: K, Q, J, 10).
   * *Note:* 4 Aces are "100" (10 pts) in Hokum, but "400" (40 pts) in Sun.
   * *Note:* A Sequence 100 beats a 4-of-a-Kind 100.

4. **50** (Sequence of 4 cards)
5. **Sira** (Sequence of 3 cards)

#### **B. Tie-Breaking Logic (Equal Projects)**

If Team A has "Sira" and Team B has "Sira":

1. **Rank Check:** Compare the highest card in the sequence. (e.g., Sira ending in Ace > Sira ending in King).
2. **Position Check (The "First" Rule):** If ranks are identical (e.g., both have Sira to the 9), the player who played **earlier** in the turn order (closest to the Dealer's right) wins.
   * *System Function:* `getTurnIndex(player)` where 0 is the starter. Lower index wins ties.

#### **C. The "Team Inheritance" Rule**

* **Winner Takes All:** If Team A's project beats Team B's project, Team A scores **ALL** their projects (even small ones), and Team B scores **ZERO** (even if their small projects are valid).
* *Example:*
   * Player 1 (Team A): Has "400".
   * Player 2 (Team B): Has "100".
   * Player 3 (Team A): Has "Sira".

* *Result:* Team A's "400" beats Team B's "100". Therefore, Team A scores for the "400" AND the "Sira". Team B gets nothing.

---

### 3. Visual Presentation: "The Show"

Visualizing the projects requires two distinct stages to mimic real life.

#### **Stage 1: The Bubble (Trick 1)**

* **Action:** When a player clicks the button, a speech bubble appears next to their avatar.
* **Content:** "Sira", "50", "100".
* **Duration:** Remains visible until the end of Trick 1.
* **Privacy:** Does *not* show which cards are involved, only the type of project.

#### **Stage 2: The Reveal (Start of Trick 2)**

This is where the system automatically resolves the conflict.

* **Timing:** After Trick 1 is collected, but before the leading player throws for Trick 2.
* **Animation:**
   1. The system identifies the winning team.
   2. The specific cards forming the project in the winner's hand **glow** or **pop up**.
   3. A mini-window overlay appears in the center of the board showing the winning cards face-up (e.g., K♦ Q♦ J♦).
   4. **Score Update:** Points are visibly added to the scoreboard (e.g., "+4").
   5. **Rejection:** The losing team's bubbles turn grey or show a "Broken" icon.

#### **D. The "Baloot" Special Case**

* **Definition:** King + Queen of Trumps (Hokum only).
* **Logic:** It is *never* blocked. It always scores.
* **Timing:** It is NOT declared in Trick 1. It is declared/shown immediately when the player plays the **second** card of the pair (e.g., they played King earlier, now they play Queen).
* **Visual:** A distinct "Baloot" animation triggers instantly upon playing the card.

---

### 4. Technical Roadmap: List of Functions for Antigravity

This roadmap is structured for the development team to implement the logic sequentially.

#### **Phase 1: Detection & Input**

1. `scanHandForProjects(playerID)`: Boolean function. Returns an array of possible projects (e.g., `[{type: 'Sira', rank: 13}]`).
2. `validateProjectOverlap(projectList)`: Ensures no single card is used in two *sequence* projects (e.g., cannot use King in a Sira and a 50 simultaneously).
3. `renderDeclarationButtons(availableProjects)`: UI function. Draws buttons only for valid options during `PlayerTurnState`.

#### **Phase 2: State Management**

4. `storeDeclaration(playerID, projectData)`: Saves the claim to a temporary `RoundState` object.
5. `lockDeclarations()`: Triggered at the end of Trick 1. Prevents further inputs.

#### **Phase 3: Resolution Engine (End of Trick 1)**

6. `compareTeamProjects(teamA, teamB)`:
   * Find max project for A and B.
   * Apply Hierarchy (400 > 100...).
   * Apply Tie-Breaker (Rank > Position).
   * Return `WinningTeamID`.

7. `calculatePoints(winningTeam, gameType)`:
   * If `Sun`: Sira=4, 50=10, 100=20, 400=40.
   * If `Hokum`: Sira=2, 50=5, 100=10.
   * Apply Multipliers (Double/Triple) if active.

#### **Phase 4: Visualization**

8. `animateProjectReveal(winningProjects)`:
   * Pause game flow.
   * Create modal with card sprites.
   * Wait 2.5 seconds.
   * Resume game flow.

9. `triggerBalootEffect()`: Listener on `CardPlayed` event. If card == K or Q of Trump AND partner played previously, trigger visual.

#### **Phase 5: Disputes (Optional)**

10. `verifyProjectLog()`: Backend function. If a player reports a bug, this log checks if the `scanHandForProjects` missed a combination or if `compareTeamProjects` failed the priority check.

By following this roadmap, Antigravity will possess a robust, rule-abiding Project system that handles the complex "Inheritance" and "Tie-Breaking" rules that generic card games often miss.

## Temporal Logic & Penalty Systems (ExternalApp Standards)

Based on deep research into the **ExternalApp** application's specific mechanics, particularly its session configuration and penalty systems, here is the detailed breakdown of time limits and temporal logic for the Antigravity application.

### **1. The Core Timer Architecture (Session Heartbeat)**

Time in ExternalApp is not fixed; it is a **Lobby Variable** chosen by the host before the game starts. Antigravity must replicate these specific "Speed Tiers" to cater to different player types.

| Icon | Speed Name | Time Per Turn | Target Audience |
| --- | --- | --- | --- |
| 🚀 | **Rocket (Saruokh)** | **5 Seconds** | Expert players only. High stress, relies on muscle memory. |
| 🐰 | **Rabbit (Arnab)** | **10 Seconds** | **Standard Competitive.** The most popular mode for ranked play. |
| 🐢 | **Turtle (Sulhafah)** | **30 Seconds** | Beginners or casual "Majlis" chat games. |
| ∞ | **Infinite** | No Limit | Only available in **Friendly/Private** lobbies (Non-Ranked). |

**Logic Requirement:** The server must enforce these limits strictly. If the client clock drifts, the server's authoritative timestamp prevails.

### **2. Detailed Phase Timing Breakdown**

Every interaction in the game has a specific window. Missing these windows triggers penalties or auto-actions.

#### **A. The Distribution Phase (0 - 5 Seconds)**

* **Dealing Animation:** The dealing of 32 cards is not instant. It takes approximately **3 to 4 seconds**.
* **Juice:** Cards fly from the center deck to users.
* **Input Lock:** User interaction is disabled during this 4-second window to prevent mis-clicks.

#### **B. The Bidding Phase (The "Buy" Timer)**

* **Duration:** Matches the Session Speed (e.g., 10s in Rabbit mode).
* **Visual Cue:** A circular countdown timer (green -> yellow -> red) wraps around the active player's avatar.
* **Timeout Action:**
  * If the player does *not* act within the time limit, the system defaults to **"Pass" (Bass)**.
* **Anti-AFK Logic:** If a player times out on Bidding **twice** in a row, the system marks them as "Away" and activates the Auto-Bot.

#### **C. The Project Declaration Phase (Start of Trick 1)**

* **Window:** This is critical. The "Project" buttons (Sira, 50, 100) appear **only** during the player's *first turn* to play a card.
* **Duration:** Shared with the Play Timer (e.g., you have 10s total to Declare AND Play).
* **Risk:** If a player waits until the last second to declare, they risk timing out before throwing the card, which forfeits the project.
* **Antigravity Improvement:** Pause the timer for **2 seconds** *after* a project is clicked to allow the player to select their card comfortably.

#### **D. The Play Phase (Combat)**

* **Duration:** Session Speed (5s / 10s / 30s).
* **The "Red Bar" Warning:** When **3 seconds** remain, the timer bar turns bright red and pulses. A "ticking" sound effect plays.
* **Timeout Action (Auto-Play):**
  * The system immediately throws a card.
  * **Logic:** It does *not* throw a random card. It throws the **weakest legal card** (e.g., a 7 or 8) to minimize damage to the team, unless the player is the *last* to act and can win the trick cheaply.

### **3. Special Function Timers (Interrupts)**

These are "Pause States" where the normal game loop halts.

#### **A. The "Sawa" (Claim) Timer**

When a player clicks "Sawa":

1. **Game Pauses:** The main turn timer stops.
2. **Decision Window:** Opponents are given **15 Seconds** to inspect the claimant's hand.
3. **Buttons:** "Accept" (Qubool) or "Reject/Continue" (Rafd).
4. **Timeout Default:** If opponents do not click within 15s, the system defaults to **Reject** (Safety mechanic to prevent accidental losses due to AFK).

#### **B. The "Qayd" (Restriction/Dispute) Timer**

* **Trigger Window:** A player can only click "Qayd" immediately after a move is made, before the next trick starts.
* **Investigation Time:** Once "Qayd" is clicked, the game pauses for **20-30 Seconds**.
* **Action:** The reporting player must select the specific card/move they are contesting from a log or visual selector.
* **Resolution:** If the player fails to select a reason within 30s, the Qayd is cancelled, and the game resumes (often with a "False Alarm" penalty).

### **4. Disconnect & Reconnect Timings**

ExternalApp is strict about connectivity to protect ranked integrity.

* **The "Yellow Signal":** If a player's ping exceeds 500ms, a yellow connection icon appears.
* **Disconnect Threshold:** If no packet is received for **15 Seconds**, the player is flagged "Disconnected."
* **Bot Takeover:** The AI immediately takes control of the hand to keep the game moving.
* **Rejoin Window:** The player has until the **end of the current game (152 points)** to reconnect. If they return, they regain control *between tricks*.
* **Penalty:** If the game ends while the player is disconnected, they receive a **double Rank Point deduction**, regardless of whether their team won or lost.

### **Summary Table for Developers**

| Event | Duration (Rabbit Mode) | System Default Action on Timeout |
| --- | --- | --- |
| **Deal Animation** | 4.0 Seconds | N/A (Input Locked) |
| **Bidding Turn** | 10.0 Seconds | **Pass (Bass)** |
| **Play Card Turn** | 10.0 Seconds | **Auto-Play Lowest Legal Card** |
| **Project Reveal** | Shared w/ Turn | **Forfeit Project** |
| **Sawa Decision** | 15.0 Seconds | **Reject Claim** |
| **Qayd Selection** | 30.0 Seconds | **Cancel Qayd** |
| **Disconnect Wait** | 15.0 Seconds | **Activate Bot** |
