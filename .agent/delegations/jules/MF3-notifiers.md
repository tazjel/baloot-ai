# Jules M-F3: Port 8 Riverpod Notifiers

## Mission
Port 8 React hooks to Riverpod StateNotifier/Provider classes in `mobile/lib/state/`.

## Context
- Project: `C:\Users\MiEXCITE\Projects\baloot-ai\mobile\`
- We use `flutter_riverpod` (NOT riverpod_generator). Manual StateNotifier classes.
- All models live in `mobile/lib/models/` (already created in M-F1)
- Services live in `mobile/lib/services/` (socket_service.dart, sound_service.dart, accounting_engine.dart already exist)
- State files go in `mobile/lib/state/` and `mobile/lib/state/ui/`
- Tests go in `mobile/test/state/`

## Pattern to Follow

Each notifier should follow this exact pattern:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

class FooNotifier extends StateNotifier<FooState> {
  FooNotifier() : super(const FooState());

  // Methods that mutate state
  void doSomething() {
    state = state.copyWith(field: newValue);
  }
}

// Provider declaration
final fooProvider = StateNotifierProvider<FooNotifier, FooState>((ref) {
  return FooNotifier();
});
```

For computed/derived providers, use `Provider<T>`:
```dart
final derivedProvider = Provider<SomeType>((ref) {
  final gameState = ref.watch(gameStateProvider);
  return computeSomething(gameState);
});
```

## Files to Create (8 notifiers + tests)

### 1. `mobile/lib/state/bidding_logic.dart`
Port of `frontend/src/hooks/useBiddingLogic.ts` (152 lines)

**TypeScript source behavior:**
- `handleBiddingAction(playerIndex, action, payload?)` — handles PASS, SUN, HOKUM, ASHKAL bids
- On PASS: advance to next player; if all passed in R1 → go to R2; if all passed R2 → redeal (rotate dealer)
- On SUN/HOKUM/ASHKAL: set bid, distribute remaining cards, detect projects, transition to Playing phase
- Plays bid sounds (pass/sun/hokum) via SoundService
- Handles ASHKAL as SUN variant where partner picks up floor card

**Dart implementation:**
```dart
class BiddingLogicNotifier extends StateNotifier<void> {
  final Ref ref;
  BiddingLogicNotifier(this.ref) : super(null);

  void handleBiddingAction(int playerIndex, String action, {Map<String, dynamic>? payload}) {
    // Read current game state from gameStateProvider
    // Mutate via ref.read(gameStateProvider.notifier).updateState(...)
    // Play sounds via SoundService()
  }
}
```

Note: This notifier is stateless (void state) — it just reads/writes the master GameState. The actual game state lives in `gameStateProvider`.

### 2. `mobile/lib/state/playing_logic.dart`
Port of `frontend/src/hooks/usePlayingLogic.ts` (121 lines)

**TypeScript source behavior:**
- `handleCardPlay(playerIndex, cardIndex, metadata?)` — plays a card from hand to table
- Removes card from player hand, adds to tableCards with position
- If 4 cards on table → sets isTrickTransitioning = true
- Otherwise advances turn to next player
- Plays card sound on every play
- `handleDoublingAction(playerIndex)` — escalates doubling level (NORMAL→DOUBLE→TRIPLE)

**Dart implementation:**
```dart
class PlayingLogicNotifier extends StateNotifier<void> {
  final Ref ref;
  PlayingLogicNotifier(this.ref) : super(null);

  void handleCardPlay(int playerIndex, int cardIndex, {Map<String, dynamic>? metadata}) { ... }
  void handleDoublingAction(int playerIndex) { ... }
}
```

### 3. `mobile/lib/state/ui/connection_status_notifier.dart`
Port of `frontend/src/hooks/useConnectionStatus.ts` (27 lines)

**TypeScript source behavior:**
- Listens to `socketService.onConnectionStatus()` for status changes
- Tracks `status` ('connected'|'disconnected'|'reconnecting') and `reconnectAttempt` count
- Resets attempt to 0 on 'connected'

**Dart implementation:**
```dart
class ConnectionState {
  final String status; // 'connected', 'disconnected', 'reconnecting'
  final int reconnectAttempt;
  const ConnectionState({this.status = 'disconnected', this.reconnectAttempt = 0});
  ConnectionState copyWith({String? status, int? reconnectAttempt}) => ConnectionState(
    status: status ?? this.status,
    reconnectAttempt: reconnectAttempt ?? this.reconnectAttempt,
  );
}

class ConnectionStatusNotifier extends StateNotifier<ConnectionState> {
  Function()? _unsubscribe;
  ConnectionStatusNotifier() : super(const ConnectionState()) {
    _unsubscribe = SocketService.instance.onConnectionStatus((status, attempt) {
      state = ConnectionState(
        status: status.name, // ConnectionStatus enum .name
        reconnectAttempt: status == ConnectionStatus.connected ? 0 : (attempt ?? state.reconnectAttempt),
      );
    });
  }

  @override
  void dispose() {
    _unsubscribe?.call();
    super.dispose();
  }
}
```

### 4. `mobile/lib/state/ui/shop_notifier.dart`
Port of `frontend/src/hooks/useShop.ts` (53 lines)

**TypeScript source behavior:**
- Manages `isStoreOpen`, `ownedItems`, `equippedItems` state
- Debounced localStorage persistence (500ms) with flush-on-dispose
- `handlePurchase(itemId, cost)` — checks canAfford, deducts coins, adds to owned
- `handleEquip(itemId, type)` — equips card back or table skin

**Dart implementation:**
- Use `shared_preferences` for persistence
- State class: `ShopState(isOpen, ownedItems, equippedCard, equippedTable)`

### 5. `mobile/lib/state/ui/tension_notifier.dart`
Port of `frontend/src/hooks/useGameTension.ts` (46 lines)

**TypeScript source behavior:**
- Computed from gameState matchScores
- 4 tension levels: low (bpm=0), medium (60), high (80), critical (100)
- Critical: maxScore >= 145
- High: maxScore > 100 AND diff < 20
- Medium: doubling phase or sawa active

**Dart implementation: Use a computed Provider (NOT StateNotifier)**
```dart
enum TensionLevel { low, medium, high, critical }

class TensionState {
  final TensionLevel level;
  final int bpm;
  const TensionState({this.level = TensionLevel.low, this.bpm = 0});
}

final tensionProvider = Provider<TensionState>((ref) {
  final gameState = ref.watch(gameStateProvider);
  // Compute tension from matchScores
});
```

### 6. `mobile/lib/state/ui/hint_notifier.dart`
Port of `frontend/src/hooks/useHintSystem.ts` (50 lines)

**TypeScript source behavior:**
- `hint` (nullable result), `isHintVisible` bool
- `requestHint()` — only works on my turn, in bidding/playing phase, if hints enabled
- `dismissHint()` — hides hint
- Auto-clears when turn or phase changes

**Dart implementation:**
```dart
class HintState {
  final Map<String, dynamic>? hint;
  final bool isVisible;
  const HintState({this.hint, this.isVisible = false});
  HintState copyWith({Map<String, dynamic>? hint, bool? isVisible}) => ...;
}

class HintNotifier extends StateNotifier<HintState> {
  final Ref ref;
  HintNotifier(this.ref) : super(const HintState());

  void requestHint() { ... } // Calls HintService
  void dismissHint() { state = state.copyWith(isVisible: false); }
  void clearOnTurnChange() { state = const HintState(); }
}
```

### 7. `mobile/lib/state/game_rules_provider.dart`
Port of `frontend/src/hooks/useGameRules.ts` (59 lines)

**TypeScript source behavior:**
- Computed from gameState: availableProjects, isCardPlayable, checkMoveLegality, sortedHand
- `availableProjects` — detected only when playing, my turn, hand.length == 8
- `isCardPlayable(card)` — permissive (just checks phase + turn)
- `checkMoveLegality(card)` — strict isValidMove check for UI warnings
- `sortedHand` — sorted by mode + trump

**Dart implementation: Pure computed Provider**
```dart
class GameRulesState {
  final List<String> availableProjects; // ProjectType values
  final List<CardModel> sortedHand;
  const GameRulesState({this.availableProjects = const [], this.sortedHand = const []});
}

final gameRulesProvider = Provider<GameRulesState>((ref) {
  final gameState = ref.watch(gameStateProvider);
  // Compute from gameState using utils
});
```

### 8. `mobile/lib/state/ui/emote_notifier.dart`
Port of `frontend/src/hooks/useEmotes.ts` (59 lines)

**TypeScript source behavior:**
- `isEmoteMenuOpen`, `flyingItems` list
- `handleSendEmote(msg)` — sends text emote
- `handleThrowItem(itemId)` — throws item toward target position (1=right, 2=top, 3=left)
- Flying items auto-remove after 1 second
- Plays shuffle sound on throw

**Dart implementation:**
```dart
class FlyingItem {
  final String id;
  final String type;
  final double startX, startY, endX, endY;
  const FlyingItem({...});
}

class EmoteState {
  final bool isMenuOpen;
  final List<FlyingItem> flyingItems;
  const EmoteState({this.isMenuOpen = false, this.flyingItems = const []});
  EmoteState copyWith({bool? isMenuOpen, List<FlyingItem>? flyingItems}) => ...;
}
```

## Tests to Create

### `mobile/test/state/bidding_logic_test.dart`
- Test PASS advances turn correctly
- Test all 3 pass in R1 → R2
- Test SUN bid sets correct state (phase=Playing, bid.type=SUN)
- Test HOKUM bid distributes cards and sets trump suit

### `mobile/test/state/playing_logic_test.dart`
- Test card play removes card from hand, adds to table
- Test 4 cards → isTrickTransitioning = true
- Test turn advances after play
- Test doubling escalation

### `mobile/test/state/tension_test.dart`
- Test low tension at start (scores 0-0)
- Test critical at 145+
- Test high at 100+ with diff < 20
- Test medium during doubling

### `mobile/test/state/connection_status_test.dart`
- Basic state transitions

## Dependencies Available
- `flutter_riverpod` — already in pubspec.yaml
- Models: `package:baloot_ai/models/` (all model classes)
- Services: `package:baloot_ai/services/socket_service.dart`, `sound_service.dart`, `accounting_engine.dart`
- Utils: `package:baloot_ai/utils/` (scoring_utils, trick_utils, project_utils, sort_utils, deck_utils, akka_utils)

## Important Notes
- Import the `gameStateProvider` from `package:baloot_ai/state/providers.dart` (will be created by Claude MAX)
- For now, if `gameStateProvider` doesn't exist yet, define a placeholder:
  ```dart
  // Placeholder — will be wired by Claude MAX
  // final gameStateProvider = StateNotifierProvider<GameStateNotifier, GameState>(...);
  ```
- DO NOT create `providers.dart` — Claude MAX will create it
- Each file should have comprehensive dartdoc comments explaining the port origin
- Follow the singleton pattern for services: `SoundService()`, `SocketService.instance`
