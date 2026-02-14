# Mission 18: "The Showman" — Game Feel & Polish

## Goal
Make the game feel alive with animations, expanded sound design, visual polish, and mobile support.

## Deliverables

### 18.1 Card Animations (`frontend/src/hooks/useCardAnimation.ts`)
- **Deal**: Cards fly from deck to hand in sequence (0.15s/card, staggered)
- **Play**: Card slides hand → table center with slight rotation (0.3s ease-out)
- **Trick-win**: 4 cards slide toward winner's avatar, scale down, fade (0.5s)
- **Trump glow**: Trump suit cards have subtle golden border shimmer
- **Kaboot**: Screen-wide confetti + card cascade + "كبوت!" text explosion

### 18.2 Sound Design (expand existing `SoundManager.ts`)
- **Card sounds**: Refined tones for play/win/lose trick
- **Bid sounds**: Pass=soft thud, Hokum=confident chime, Sun=bright fanfare, Double=dramatic drum
- **Tension**: Wire to existing `useGameTension` — ambient drone at high, heartbeat at critical
- **Victory/defeat jingle**: 2-3s musical stinger
- **Kaboot sound**: Dramatic boom + brass
- **Volume controls**: Per-category sliders in Settings (Music, SFX, Ambient)

### 18.3 Visual Polish
- Table felt texture (CSS gradient)
- Dynamic card shadows (soft in-hand, sharp played, glow highlighted)
- Pulsing golden turn indicator ring
- Score animation (count up/down with easing)
- Bid indicator chips (poker-style on table)
- Dark/light theme toggle

### 18.4 Mobile Experience
- Responsive card fan at < 480px
- Touch gestures: swipe to play, long-press preview
- Bottom-sheet modals on mobile
- Portrait layout optimization

## Key Constraint
- Use CSS transitions + requestAnimationFrame, no animation libraries
- All sounds synthesized via Web Audio API (existing SoundManager pattern)
- Animations must be disable-able in Settings for accessibility
