# Gemini M-F3: Port 4 Audio/UI Riverpod Notifiers

## Mission
Port 4 React hooks to Riverpod StateNotifier/Provider classes. These handle audio reactivity, bot speech, toast notifications, and match replay.

## Context
- Project: `C:\Users\MiEXCITE\Projects\baloot-ai\mobile\`
- We use `flutter_riverpod` (NOT riverpod_generator). Manual StateNotifier classes.
- All models live in `mobile/lib/models/`
- Services: `mobile/lib/services/sound_service.dart` (YOU created this in M-F2)
- State files go in `mobile/lib/state/audio/` and `mobile/lib/state/ui/`
- Tests go in `mobile/test/state/`

## Pattern

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

class FooNotifier extends StateNotifier<FooState> {
  FooNotifier() : super(const FooState());
  void doSomething() {
    state = state.copyWith(field: newValue);
  }
}

final fooProvider = StateNotifierProvider<FooNotifier, FooState>((ref) {
  return FooNotifier();
});
```

## Files to Create (4 notifiers + tests)

### 1. `mobile/lib/state/audio/audio_notifier.dart`
Port of `frontend/src/hooks/useGameAudio.ts` (165 lines)

**TypeScript source behavior:**
- Tracks previous state via refs to detect CHANGES (not absolute state)
- Auto-plays sounds when specific state transitions occur:
  1. **Your turn**: currentTurnIndex becomes 0 + phase == Playing → play turn sound + toast "دورك — العب ورقة"
  2. **Trick completion**: tableCards length goes 4 → 0 → play win sound + toast with winner
  3. **Akka declared**: akkaState gets a new claimer → play akka sound + toast
  4. **Sawa claimed**: sawaState.active becomes true → toast
  5. **Project reveal**: isProjectRevealing becomes true → toast
  6. **Phase transition**: phase changes to Playing → toast "بداية اللعب"
- Provides: speakAction(), playCardSound(), playWinSound(), playAkkaSound(), playErrorSound()

**Dart implementation:**
```dart
class AudioNotifier extends StateNotifier<AudioState> {
  final Ref ref;
  final SoundService _sound = SoundService();

  // Previous state trackers
  int _prevTurnIndex = -1;
  int _prevTableLength = 0;
  dynamic _prevAkkaClaimer;
  bool _prevSawaActive = false;
  bool _prevProjectRevealing = false;
  GamePhase? _prevPhase;

  AudioNotifier(this.ref) : super(const AudioState());

  /// Call this whenever gameState changes to check for sound triggers
  void onGameStateChanged(GameState gameState) {
    // 1. Your turn detection
    final isMyTurn = gameState.currentTurnIndex == 0;
    final wasMyTurn = _prevTurnIndex == 0;
    if (isMyTurn && !wasMyTurn && gameState.phase == GamePhase.playing) {
      _sound.playTurnSound();
      // Could also trigger toast via ref
    }
    _prevTurnIndex = gameState.currentTurnIndex;

    // 2. Trick completion (4 → 0 cards)
    final tableLen = gameState.tableCards.length;
    if (_prevTableLength == 4 && tableLen == 0) {
      _sound.playWinSound();
    }
    _prevTableLength = tableLen;

    // 3. Akka, Sawa, Project, Phase transitions...
    // (similar pattern for each)
  }

  void playCardSound() => _sound.playCardSound();
  void playErrorSound() => _sound.playErrorSound();
}

class AudioState {
  const AudioState();
}
```

**Key insight**: This notifier is primarily a side-effect handler (plays sounds). It watches game state changes and triggers audio. The state itself is minimal — it's the reactivity that matters.

### 2. `mobile/lib/state/audio/bot_speech_notifier.dart`
Port of `frontend/src/hooks/useBotSpeech.ts` (79 lines)

**TypeScript source behavior:**
- Listens to `bot_speak` socket events
- Maps player avatar to voice personality (khalid→AGGRESSIVE, abu_fahad→CONSERVATIVE, others→BALANCED)
- Sets speech text per player index
- Auto-clears speech after 5 seconds
- Cancels previous timer for same player (prevents overlapping)
- Uses TTS (flutter_tts) to speak the text

**Dart implementation:**
```dart
class BotSpeechState {
  final Map<int, String?> playerSpeech; // playerIndex → speech text (null = no speech)
  const BotSpeechState({this.playerSpeech = const {}});
  BotSpeechState copyWith({Map<int, String?>? playerSpeech}) =>
    BotSpeechState(playerSpeech: playerSpeech ?? this.playerSpeech);
}

class BotSpeechNotifier extends StateNotifier<BotSpeechState> {
  Function()? _unsubscribe;
  final Map<int, Timer> _speechTimers = {};

  BotSpeechNotifier() : super(const BotSpeechState()) {
    _unsubscribe = SocketService.instance.onBotSpeak((playerIndex, text, emotion) {
      // Set speech for this player
      state = state.copyWith(playerSpeech: {...state.playerSpeech, playerIndex: text});

      // TTS
      _speak(text, playerIndex);

      // Cancel previous timer, set new 5-second auto-clear
      _speechTimers[playerIndex]?.cancel();
      _speechTimers[playerIndex] = Timer(Duration(seconds: 5), () {
        if (mounted) {
          final newSpeech = Map<int, String?>.from(state.playerSpeech);
          if (newSpeech[playerIndex] == text) {
            newSpeech[playerIndex] = null;
          }
          state = state.copyWith(playerSpeech: newSpeech);
        }
      });
    });
  }

  void _speak(String text, int playerIndex) {
    // Use flutter_tts package
  }

  @override
  void dispose() {
    _unsubscribe?.call();
    _speechTimers.values.forEach((t) => t.cancel());
    super.dispose();
  }
}
```

### 3. `mobile/lib/state/ui/toast_notifier.dart`
Port of `frontend/src/hooks/useGameToast.ts` (69 lines)

**TypeScript source behavior:**
- Toast types: 'turn', 'akka', 'sawa', 'project', 'trick', 'error', 'info', 'baloot', 'kaboot'
- `addToast(message, type, icon)` — adds with dedup (1.5s window), max 3 on screen
- Auto-dismiss after 3 seconds
- `dismissToast(id)` — manual removal with timer cleanup

**Dart implementation:**
```dart
class Toast {
  final String id;
  final String message;
  final String type; // ToastType enum value
  final String icon;
  final int timestamp;
  const Toast({required this.id, required this.message, required this.type, required this.icon, required this.timestamp});
}

class ToastState {
  final List<Toast> toasts;
  const ToastState({this.toasts = const []});
  ToastState copyWith({List<Toast>? toasts}) => ToastState(toasts: toasts ?? this.toasts);
}

class ToastNotifier extends StateNotifier<ToastState> {
  static const _toastDuration = Duration(seconds: 3);
  static const _maxToasts = 3;
  static const _dedupWindow = Duration(milliseconds: 1500);

  final Map<String, Timer> _timerMap = {};
  String? _lastMessage;
  int _lastMessageTime = 0;

  ToastNotifier() : super(const ToastState());

  void addToast(String message, String type, {String icon = '📢'}) {
    final now = DateTime.now().millisecondsSinceEpoch;

    // Dedup check
    if (_lastMessage == message && (now - _lastMessageTime) < _dedupWindow.inMilliseconds) {
      return;
    }
    _lastMessage = message;
    _lastMessageTime = now;

    final id = 'toast-$now-${now.hashCode.toRadixString(36).substring(0, 4)}';
    final toast = Toast(id: id, message: message, type: type, icon: icon, timestamp: now);

    state = state.copyWith(
      toasts: [toast, ...state.toasts].take(_maxToasts).toList(),
    );

    // Auto-remove
    _timerMap[id] = Timer(_toastDuration, () {
      _timerMap.remove(id);
      state = state.copyWith(toasts: state.toasts.where((t) => t.id != id).toList());
    });
  }

  void dismissToast(String id) {
    _timerMap[id]?.cancel();
    _timerMap.remove(id);
    state = state.copyWith(toasts: state.toasts.where((t) => t.id != id).toList());
  }

  @override
  void dispose() {
    _timerMap.values.forEach((t) => t.cancel());
    _timerMap.clear();
    super.dispose();
  }
}
```

### 4. `mobile/lib/state/ui/replay_notifier.dart`
Port of `frontend/src/hooks/useReplayNavigation.ts` (81 lines)

**TypeScript source behavior:**
- State: selectedRoundIdx, selectedTrickIdx, isPlaying
- Auto-play at 1.5s intervals, stops at end of round
- Navigation: nextTrick, prevTrick, nextRound, prevRound, selectRound, togglePlay
- Uses ref for tricks.length to avoid interval restarts

**Dart implementation:**
```dart
class ReplayState {
  final int selectedRoundIdx;
  final int selectedTrickIdx;
  final bool isPlaying;
  final List<dynamic> matchHistory; // Provided externally
  const ReplayState({...});
  ReplayState copyWith({...}) => ...;
}

class ReplayNotifier extends StateNotifier<ReplayState> {
  Timer? _playTimer;

  ReplayNotifier() : super(const ReplayState());

  void setMatchHistory(List<dynamic> history) { ... }
  void nextTrick() { ... }
  void prevTrick() { ... }
  void nextRound() { ... }
  void prevRound() { ... }
  void selectRound(int idx) { ... }
  void togglePlay() {
    if (state.isPlaying) {
      _playTimer?.cancel();
      state = state.copyWith(isPlaying: false);
    } else {
      state = state.copyWith(isPlaying: true);
      _startAutoPlay();
    }
  }
  void _startAutoPlay() {
    _playTimer = Timer.periodic(Duration(milliseconds: 1500), (_) {
      // Advance trick or stop at end
    });
  }

  @override
  void dispose() {
    _playTimer?.cancel();
    super.dispose();
  }
}
```

## Tests to Create

### `mobile/test/state/toast_notifier_test.dart`
- addToast adds toast to list
- Max 3 toasts enforced
- Dedup within 1.5s window works
- dismissToast removes correct toast

### `mobile/test/state/replay_notifier_test.dart`
- nextTrick/prevTrick navigation
- Round navigation
- Auto-play starts and stops

### `mobile/test/state/bot_speech_test.dart`
- Speech state updates per player
- Auto-clear after timeout

## Dependencies
- `flutter_riverpod` — in pubspec.yaml
- `flutter_tts` — in pubspec.yaml (for bot speech)
- `package:baloot_ai/services/sound_service.dart` (YOU created this)
- `package:baloot_ai/services/socket_service.dart`
- Models: `package:baloot_ai/models/`

## Important Notes
- Import the `gameStateProvider` from `package:baloot_ai/state/providers.dart` (Claude MAX will create)
- For AudioNotifier, you need to watch game state changes. The pattern:
  ```dart
  // In the provider definition, watch gameState and call onGameStateChanged
  final audioProvider = StateNotifierProvider<AudioNotifier, AudioState>((ref) {
    final notifier = AudioNotifier(ref);
    // Listen to game state changes
    ref.listen(gameStateProvider, (prev, next) {
      notifier.onGameStateChanged(next);
    });
    return notifier;
  });
  ```
- Each file should have comprehensive dartdoc comments
- Follow singleton pattern for services: `SoundService()`, `SocketService.instance`
- Use `dart:async` Timer for auto-clear timers (NOT Future.delayed, which can't be cancelled)
