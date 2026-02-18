/// game_state_notifier.dart — Master game state manager.
///
/// Port of frontend/src/hooks/useGameState.ts (174 lines).
///
/// This is the central Riverpod StateNotifier that owns the [GameState].
/// All other notifiers read from and write to this single source of truth.
///
/// ## Responsibilities
/// - Owns the canonical [GameState] instance
/// - Provides mutation methods for all subsystems (socket, bidding, playing, round)
/// - Manages system messages queue
/// - Preserves local settings across server state updates
///
/// ## Architecture
/// ```
/// GameStateNotifier (this file)
///   ├── GameSocketNotifier   — socket events → updateState()
///   ├── BiddingLogicNotifier  — handleBiddingAction → updateState()
///   ├── PlayingLogicNotifier  — handleCardPlay → updateState()
///   ├── RoundManager          — completeTrick → updateState()
///   └── ActionDispatcher      — routes to above based on phase
/// ```
library;
import 'dart:developer' as dev;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/bid.dart';
import '../models/enums.dart';
import '../models/game_settings.dart';
import '../models/game_state.dart';
import '../models/player.dart';

/// System message for the chat log.
class SystemMessage {
  final String sender;
  final String text;
  final DateTime timestamp;

  const SystemMessage({
    this.sender = 'النظام',
    required this.text,
    required this.timestamp,
  });
}

/// Combined state container for the game + UI metadata.
class AppGameState {
  final GameState gameState;
  final List<SystemMessage> messages;
  final bool isCuttingDeck;
  final DateTime? turnStartTime;

  const AppGameState({
    required this.gameState,
    this.messages = const [],
    this.isCuttingDeck = false,
    this.turnStartTime,
  });

  AppGameState copyWith({
    GameState? gameState,
    List<SystemMessage>? messages,
    bool? isCuttingDeck,
    DateTime? turnStartTime,
  }) {
    return AppGameState(
      gameState: gameState ?? this.gameState,
      messages: messages ?? this.messages,
      isCuttingDeck: isCuttingDeck ?? this.isCuttingDeck,
      turnStartTime: turnStartTime ?? this.turnStartTime,
    );
  }
}

/// Default initial game state matching the TypeScript INITIAL_GAME_STATE.
final _initialGameState = GameState(
  players: const [
    Player(
      position: PlayerPosition.bottom,
      name: 'أنا',
      avatar: 'default',
      index: 0,
      isActive: true,
    ),
    Player(
      position: PlayerPosition.right,
      name: 'خالد',
      avatar: 'khalid',
      index: 1,
      isBot: true,
    ),
    Player(
      position: PlayerPosition.top,
      name: 'أبو فهد',
      avatar: 'abu_fahad',
      index: 2,
      isBot: true,
    ),
    Player(
      position: PlayerPosition.left,
      name: 'سعد',
      avatar: 'saad',
      index: 3,
      isBot: true,
      isDealer: true,
    ),
  ],
  currentTurnIndex: 0,
  phase: GamePhase.waiting,
  tableCards: const [],
  bid: const Bid.empty(),
  teamScores: const TeamScores(),
  matchScores: const TeamScores(),
  floorCard: null,
  dealerIndex: 3,
  biddingRound: 1,
  declarations: const {},
  doublingLevel: DoublingLevel.normal,
  isLocked: false,
  roundHistory: const [],
  deck: const [],
  lastTrick: null,
);

/// Master game state notifier.
///
/// All game state mutations flow through this notifier. Sub-notifiers
/// (bidding, playing, round manager) call [updateState] or [updateGameState]
/// to apply their changes.
class GameStateNotifier extends StateNotifier<AppGameState> {
  GameStateNotifier()
      : super(AppGameState(
          gameState: _initialGameState,
          turnStartTime: DateTime.now(),
        ));

  // =========================================================================
  // State Access
  // =========================================================================

  /// The current game state (convenience getter).
  GameState get gameState => state.gameState;

  /// System messages list.
  List<SystemMessage> get messages => state.messages;

  // =========================================================================
  // State Mutation — Full Replacement
  // =========================================================================

  /// Replace the entire game state (used by socket updates).
  ///
  /// Preserves local settings from the previous state, since the server
  /// doesn't track client-side settings (theme, sound, hints, etc.).
  void setGameStateFromServer(GameState newState) {
    state = state.copyWith(
      gameState: newState.copyWith(
        settings: state.gameState.settings,
      ),
      turnStartTime: DateTime.now(),
    );
    dev.log(
      'Game Update: phase=${newState.phase.value}, turn=${newState.currentTurnIndex}',
      name: 'STATE',
    );
  }

  /// Replace the game state without preserving settings (for local mutations).
  void setGameState(GameState newState) {
    state = state.copyWith(
      gameState: newState,
      turnStartTime: DateTime.now(),
    );
  }

  /// Apply a mutation function to the current game state.
  ///
  /// This is the primary mutation pattern for sub-notifiers:
  /// ```dart
  /// ref.read(gameStateProvider.notifier).updateGameState((prev) {
  ///   return prev.copyWith(phase: GamePhase.playing);
  /// });
  /// ```
  void updateGameState(GameState Function(GameState prev) updater) {
    final newGameState = updater(state.gameState);
    state = state.copyWith(
      gameState: newGameState,
      turnStartTime: DateTime.now(),
    );
  }

  // =========================================================================
  // System Messages
  // =========================================================================

  /// Add a system message to the chat log.
  void addSystemMessage(String text) {
    final msg = SystemMessage(text: text, timestamp: DateTime.now());
    state = state.copyWith(
      messages: [...state.messages, msg],
    );
  }

  // =========================================================================
  // Settings Management
  // =========================================================================

  /// Update game settings locally.
  void updateSettings(GameSettings newSettings) {
    state = state.copyWith(
      gameState: state.gameState.copyWith(settings: newSettings),
    );
  }

  /// Merge partial settings into the current settings.
  void mergeSettings({
    double? turnDuration,
    bool? strictMode,
    bool? soundEnabled,
    String? gameSpeed,
    BotDifficulty? botDifficulty,
    bool? isDebug,
    bool? showHints,
  }) {
    state = state.copyWith(
      gameState: state.gameState.copyWith(
        settings: state.gameState.settings.copyWith(
          turnDuration: turnDuration,
          strictMode: strictMode,
          soundEnabled: soundEnabled,
          gameSpeed: gameSpeed,
          botDifficulty: botDifficulty,
          isDebug: isDebug,
          showHints: showHints,
        ),
      ),
    );
  }

  // =========================================================================
  // Deck Cutting (UI animation state)
  // =========================================================================

  /// Set the deck-cutting animation state.
  void setIsCuttingDeck(bool value) {
    state = state.copyWith(isCuttingDeck: value);
  }

  // =========================================================================
  // Reset
  // =========================================================================

  /// Reset to initial state (e.g., on logout or leave room).
  void reset() {
    state = AppGameState(
      gameState: _initialGameState,
      turnStartTime: DateTime.now(),
    );
  }
}
