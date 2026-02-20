/// providers.dart — Central Riverpod provider declarations.
///
/// This file is the single source of truth for all game-related providers.
/// Every notifier and computed provider is declared here to avoid circular
/// imports and ensure a clean dependency graph.
///
/// ## Provider Hierarchy
/// ```
/// gameStateProvider (master state)
///   ├── gameSocketProvider (socket communication)
///   ├── biddingLogicProvider (bid actions)
///   ├── playingLogicProvider (card play + doubling)
///   ├── roundManagerProvider (round lifecycle)
///   ├── actionDispatcherProvider (action routing facade)
///   ├── audioNotifierProvider (sound triggers)
///   ├── botSpeechProvider (bot TTS)
///   ├── toastProvider (toast notifications)
///   ├── replayProvider (match replay)
///   ├── connectionStatusProvider (socket status)
///   ├── shopProvider (store management)
///   ├── tensionProvider (game tension level)
///   ├── hintProvider (AI hints)
///   ├── gameRulesProvider (computed legal moves)
///   └── emoteProvider (emotes + flying items)
/// ```
///
/// ## Usage
/// ```dart
/// // Read current game state
/// final appState = ref.watch(gameStateProvider);
/// final gameState = appState.gameState;
///
/// // Mutate game state
/// ref.read(gameStateProvider.notifier).updateGameState((prev) => ...);
///
/// // Send action
/// ref.read(actionDispatcherProvider.notifier).handlePlayerAction('PLAY', payload: {...});
/// ```
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_notifier.dart';
import 'game_state_notifier.dart';
import 'game_socket_notifier.dart';
import 'round_manager.dart';
import 'action_dispatcher.dart';
import 'bidding_logic.dart';
import 'playing_logic.dart';

// Re-export computed providers declared in their own files
export 'game_rules_provider.dart' show gameRulesProvider;

// =============================================================================
// Authentication
// =============================================================================

/// Authentication state provider.
///
/// Manages JWT token persistence, user profile, and auth lifecycle.
/// Orthogonal to game state — no dependency on gameStateProvider.
final authProvider =
    StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});

// =============================================================================
// Core Game State
// =============================================================================

/// Master game state provider.
///
/// Owns the canonical [AppGameState] (which contains [GameState] + messages).
/// All other providers read from and write to this single source of truth.
final gameStateProvider =
    StateNotifierProvider<GameStateNotifier, AppGameState>((ref) {
  return GameStateNotifier();
});

// =============================================================================
// Socket Communication
// =============================================================================

/// Socket connection and room management provider.
///
/// Manages the Socket.IO connection to the Python backend, handles
/// action dispatching, and applies rotated game state updates.
final gameSocketProvider =
    StateNotifierProvider<GameSocketNotifier, SocketState>((ref) {
  return GameSocketNotifier(ref);
});

// =============================================================================
// Game Logic
// =============================================================================

/// Round lifecycle manager provider.
///
/// Handles new round setup, trick completion, and round scoring.
/// Only active during offline/local play — the server handles
/// round management when connected.
final roundManagerProvider =
    StateNotifierProvider<RoundManager, void>((ref) {
  return RoundManager(ref);
});

/// Action routing facade provider.
///
/// Routes all player actions to the appropriate handler based on
/// game phase and connection state.
final actionDispatcherProvider =
    StateNotifierProvider<ActionDispatcher, ActionDispatcherState>((ref) {
  return ActionDispatcher(ref);
});

// =============================================================================
// Bidding & Playing Logic
// =============================================================================

/// Bidding logic provider.
///
/// Handles PASS, SUN, HOKUM, ASHKAL bid actions.
/// Manages floor card pickup, card distribution, project detection,
/// and phase transitions from bidding to playing.
final biddingLogicProvider =
    StateNotifierProvider<BiddingLogicNotifier, void>((ref) {
  return BiddingLogicNotifier(ref);
});

/// Playing logic provider.
///
/// Handles card play and doubling actions.
/// Manages hand updates, table card placement, trick transitions,
/// and doubling level escalation.
final playingLogicProvider =
    StateNotifierProvider<PlayingLogicNotifier, void>((ref) {
  return PlayingLogicNotifier(ref);
});
