# Frontend Guide 🎨

**For**: Frontend Developers & Designers.
**Purpose**: Understand the React architecture, state management, and UI systems of the Baloot web app.

## 🏗️ Architecture Overview

The frontend is a **Single Page Application (SPA)** built with:
- **React 18** (Vite)
- **TypeScript** (Strict Mode)
- **Tailwind CSS** (Styling)
- **Framer Motion** (Animations)
- **Socket.IO Client** (Real-time communication)

### Directory Structure

Unlike standard React apps, we prioritize a flat structure for core logical components.

| Path | Purpose |
|------|---------|
| `App.tsx` | **Main Controller**. Handles Routing (View Switching), Global Modals, and Sound initialization. |
| `components/` | All UI components. |
| `components/Table.tsx` | **The Game Board**. Renders players, cards, and the floor. |
| `hooks/useGameState.ts` | **The Brain**. Custom hook that manages all socket events and local state merging. |
| `services/` | API interaction (SocketService, TrainingService). |
| `index.css` | Global styles, fonts (Tajawal), and Tailwind directives. |

---

## 🧭 Navigation & Routing

We do **NOT** use `react-router` for the main game loop to ensure seamless transitions and state preservation.

**State-Based Routing (`currentView` in `App.tsx`):**
1.  **`LOBBY`**: The landing screen (Single Player, Multiplayer, AI Studio entry).
2.  **`GAME`**: The active gameplay view (`Table.tsx`).
3.  **`AI_STUDIO`**: The analysis dashboard.
4.  **`PUZZLE_LIST` / `PUZZLE_BOARD`**: The AI Classroom screens.

---

## 💾 State Management

We use a **Context-like Pattern** via a single massive custom hook: `useGameState`.

-   **Why?**: Baloot is a turn-based game where the server is the single source of truth.
-   **How it works**:
    1.  `SocketService` receives a `GAME_UPDATE` event.
    2.  `useGameState` merges valid partial updates into the local `GameState` object.
    3.  `App.tsx` passes the *entire* `gameState` down to `Table` and other children.

### Persistence (LocalStorage)
We persist user preferences and unlocked items using `localStorage`:
-   `baloot_owned_items`: Array of purchased item IDs.
-   `baloot_equipped_items`: Currently selected `{ card: string, table: string }`.
-   `user_profile`: Name, Coins, Experience.

---

## 🛠️ Key Components

### 1. `Table.tsx` (The Board)
The complex orchestrator of the game view.
-   **Responsibility**: Renders the 4 players (`PlayerAvatar`), the hand (`Hand`), and the floor cards.
-   **Coordinate System**: Uses `getRelativePlayerIndex` to ensure **YOU** are always at the bottom (Index 0).
    -   *Server Index*: 0, 1, 2, 3 (Fixed).
    -   *Visual Index*: Rotates so `myIndex` becomes 0.

### 2. `SettingsModal.tsx`
-   **Trigger**: Gear icon in `App.tsx`.
-   **Features**:
    -   **Visuals**: Change Card Skins and Table Felts (Persisted).
    -   **Audio**: Toggle SFX/Music.
    -   **Debug**: Toggle `Debug Mode` (shows AI thoughts).

### 3. `SpeechBubble.tsx` & `EmoteMenu.tsx`
-   **System**: Part of the "Voices" feature.
-   **Implementation**:
    -   Bots emit `bot_speak` events via Socket.
    -   `PlayerAvatar` renders a `SpeechBubble` with `framer-motion` for pop-in effects.
    -   Text-to-Speech (TTS) is handled via browser Native API or external service invocations.

---

## 🎨 Styling System

-   **Tailwind**: Used for 95% of styling.
-   **Glassmorphism**: Heavy use of `backdrop-blur`, `bg-white/10`, and `border-white/20`.
-   **Animations (`framer-motion`)**:
    -   `layoutId`: Used for smooth card movement from Hand -> Table -> Trick Pile.
    -   `AnimatePresence`: Used for Modals (Victory, LevelUp) entering/exiting.

## 🐛 Debugging Tips

1.  **"Where is the card?"**: Check `Card.tsx`. If a card is `null` or `undefined`, the component returns `null` to prevent crashes.
2.  **Console Noise**: We use a custom `devLogger` (`utils/devLogger.ts`). To see logs, type `debug.enable()` in the browser console (if implemented) or check the "Debug Mode" toggle in settings.
3.  **Strict Mode**: React Strict Mode is ON. Effects fire twice in dev. Be careful with socket listeners (use cleanup functions!).
