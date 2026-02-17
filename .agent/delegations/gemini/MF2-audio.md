# Gemini Task: M-F2 Audio Asset Pipeline

## Overview
Generate 16 MP3 sound files from the Web Audio API specs in SoundManager.ts,
then create the AudioService wrapper in Dart.

## Step 1: Generate MP3 Files
Read `frontend/src/services/SoundManager.ts` — it has 14 procedurally synthesized sounds using Web Audio API.
For each sound:
1. Create a small Node.js script that reproduces the exact Web Audio synthesis
2. Use `OfflineAudioContext` to render to buffer
3. Export as MP3 at 320kbps
4. Save to `mobile/assets/sounds/`

### Sound List:
1. `card_play.mp3` — playCardSound() — noise burst + triangle wave
2. `shuffle.mp3` — (create manually — card shuffle sound)
3. `deal.mp3` — (rapid card snap sequence)
4. `win_trick.mp3` — playWinSound() — coin chime (880Hz + 1760Hz)
5. `turn_ding.mp3` — playTurnSound() — glass ding (1200Hz)
6. `error_buzz.mp3` — playErrorSound() — low buzz (150Hz→100Hz)
7. `project_wow.mp3` — playProjectSound() — arpeggio (440,554,659,880Hz)
8. `akka_impact.mp3` — playAkkaSound() — impact (110Hz + 880Hz)
9. `click.mp3` — playClick() — mechanical tick (800Hz)
10. `pass_bid.mp3` — playPassSound() — muted triangle 80Hz
11. `hokum_bid.mp3` — playHokumSound() — bold sine 660Hz
12. `sun_bid.mp3` — playSunSound() — 3-note arpeggio (C6,E6,G6)
13. `double_bid.mp3` — playDoubleSound() — deep sawtooth + noise
14. `kaboot.mp3` — playKabootSound() — bass + brass
15. `victory_jingle.mp3` — playVictoryJingle() — ascending C major
16. `defeat_jingle.mp3` — playDefeatJingle() — descending minor

## Step 2: Create AudioService
Create `mobile/lib/services/sound_service.dart`:
- Use `audioplayers` package
- Preload all 16 sounds on init
- Per-category volume control (cards, ui, events, bids)
- Global mute toggle
- Methods: `playCardSound()`, `playWinSound()`, etc. (matching SoundManager API)

## Verification
- All 16 MP3 files present in mobile/assets/sounds/
- AudioService compiles without errors
- Sounds play on Android emulator
