# Kamelna UI Analysis
Based on reference video `Full_round_kamelna_Recording`

## 1. General Layout
The interface uses a **Split-Screen Layout** (approx 25% Left / 75% Right).

### Left Column: Sidebar (Control & Info)
A dark/grey panel containing:
- **Top Action Bar**: 4 Buttons (Exit, Help, Share, Sound).
- **Game Session Info**:
    - Session ID.
    - "Us" vs "Them" scores (or properties).
    - Connection/Level indicators.
- **Spectators List**: A section showing currently watching users.
- **Chat Panel**:
    - Scrollable message area.
    - Input field and "Send" button at the bottom.
    - "Voice" or "Mute" toggle button above chat?

### Right Column: Game Table
A skeuomorphic 3D-style table view.
- **Background**: Beige/Tan floor with a central Red/Green patterned carpet (Sadu style).
- **Perspective**: Top-down angled perspective.
- **Player Avatars**:
    4 Circular avatars positioned Top, Bottom, Left, Right.
    - Status/Timer rings around avatars.
    - Name and Title badges.
    - "Dealer" indicator (D).
- **Cards**:
    - **Hand**: Fanned out at the bottom center.
    - **Played Cards**: Thrown into the center of the carpet.
    - **Card Back**: Blue/Patterned design.
- **Action Buttons**: Floating buttons for game actions (Pass, Double, Project calls) appear contextually.

## 2. Key Visual Details
- **Animations**:
    - Cards "fly" to the center when played.
    - Tricks are "swept" to the winning team's side.
    - "Bid" indicators appear near players.
- **Colors**:
    - Sidebar: Dark Grey/Black background with White text/icons.
    - Table Background: Solid Beige/Sand color (`#EBE5CE` approx).
    - Carpet: Deep Red (`#8B0000`) and Green patterns.

## 3. Gap Analysis (Current vs Target)
| Feature | Current Implementation | Target (Video) |
| :--- | :--- | :--- |
| **Layout** | Single "Mobile App" container centered on screen | Fixed Sidebar (Left) + Table (Right) split |
| **Sidebar** | Exists in `Sidebar.tsx` but not integrated in main layout | Always visible on the left |
| **Background** | Wood texture | Beige/Sand color |
| **Carpet** | `premium_felt.png` | Specific Sadu pattern (Red/Green) |
| **Chat** | Hidden/Modal? | Integrated in Sidebar |

## 4. Recommendations
1.  **Refactor `GameLayout`**:
    -   Implement a flex container with `Sidebar` (Left) and `Table` (Right).
    -   Remove the "Phone Frame" wrapper for Desktop/Web view.
2.  **Theme Update**:
    -   Update background colors to match the refined beige tone.
    -   Use the specific Carpet texture if available or generate one.
3.  **Sidebar Integration**:
    -   Connect `Sidebar` to live game state (chat, scores, spectators).
