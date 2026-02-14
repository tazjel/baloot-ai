# Mission 20: "The Arena" — Multiplayer & Social Features

## Goal
Enable real online multiplayer with room management, matchmaking, and social features.

## Deliverables

### 20.1 Room System Enhancement
- **Room browser**: Lobby showing available rooms (player count, status, difficulty)
- **Private rooms**: 4-6 char codes. Host sets rules (difficulty, timer, match target)
- **Quick match**: One-click auto-join/create + fill empty seats with bots
- **Reconnection**: Hold seat 60s on disconnect, bot takes over, restore on reconnect
- **Spectator mode**: Watch games, see played cards only, chat-only

### 20.2 In-Game Communication (expand existing EmoteMenu)
- Quick chat: Arabic/English Baloot phrases ("يا سلام!", "كمل كمل", "صبر", "خلاص")
- Team-only chat (partner only, opponents can't see)
- Emote reactions to specific tricks/bids
- Mute/block per player (persists in localStorage)

### 20.3 Player Profiles
- Display name + avatar selection (8-12 presets) + level + total wins
- XP system: +10 win, +3 loss, +5 Kaboot, +2 Baloot. Levels: 0, 50, 150, 300, 500, 800, 1200...
- Level badges: Bronze (1-5), Silver (6-10), Gold (11-20), Diamond (21+)
- Leaderboard: Top 20 by win rate (min 10 games), total wins, Kaboot count

## Key Constraint
- Room state in Redis (already has room_manager.py)
- Player profiles stored server-side in SQLite/Redis
- Reconnection must handle mid-trick state restoration
- Rate limit all chat/emote events (existing rate_limiter.py)
