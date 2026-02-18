/// game_rules_provider.dart — Computed legal moves and game rules.
///
/// Port of frontend/src/hooks/useGameRules.ts (59 lines).
///
/// Provides computed/derived game state values:
/// - Legal card indices for the current player
/// - Available projects for declaration
/// - Whether the current player can double
/// - Current trump suit
///
/// These are pure computations from the game state, exposed as
/// Riverpod providers for efficient reactive access.
library;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/enums.dart';
import '../utils/trick_utils.dart';
import 'providers.dart';

/// Computed game rules from current state.
class GameRules {
  /// Indices of legally playable cards in the human player's hand.
  final List<int> legalCardIndices;

  /// Current trump suit (null for SUN mode).
  final Suit? trumpSuit;

  /// Current game mode.
  final GameMode? gameMode;

  /// Whether the human player can currently double.
  final bool canDouble;

  /// Whether it's the human player's turn.
  final bool isMyTurn;

  /// Whether the game is in a trick transition.
  final bool isTrickTransitioning;

  const GameRules({
    this.legalCardIndices = const [],
    this.trumpSuit,
    this.gameMode,
    this.canDouble = false,
    this.isMyTurn = false,
    this.isTrickTransitioning = false,
  });
}

/// Computes legal moves and game rules from current state.
///
/// This is a computed Provider (not StateNotifier) — it recomputes
/// whenever gameStateProvider changes.
final gameRulesProvider = Provider<GameRules>((ref) {
  final appState = ref.watch(gameStateProvider);
  final gameState = appState.gameState;

  // Only compute during active play
  if (gameState.phase != GamePhase.playing &&
      gameState.phase != GamePhase.bidding) {
    return const GameRules();
  }

  final isSun = gameState.bid.type == GameMode.sun;
  final trumpSuit =
      isSun ? null : (gameState.bid.suit ?? gameState.floorCard?.suit);
  final mode = isSun ? GameMode.sun : GameMode.hokum;
  final isMyTurn = gameState.currentTurnIndex == 0;

  // Compute legal card indices for the human player (index 0)
  final List<int> legalIndices = [];
  if (isMyTurn && gameState.phase == GamePhase.playing) {
    final hand = gameState.players[0].hand;
    for (int i = 0; i < hand.length; i++) {
      if (isValidMove(
        card: hand[i],
        hand: hand,
        tableCards: gameState.tableCards,
        mode: mode,
        trumpSuit: trumpSuit,
        isLocked: gameState.isLocked,
      )) {
        legalIndices.add(i);
      }
    }
  }

  // Can double: during playing phase, not already at max level
  final canDouble = gameState.phase == GamePhase.playing &&
      isMyTurn &&
      gameState.doublingLevel != DoublingLevel.gahwa &&
      gameState.tableCards.isEmpty;

  return GameRules(
    legalCardIndices: legalIndices,
    trumpSuit: trumpSuit,
    gameMode: mode,
    canDouble: canDouble,
    isMyTurn: isMyTurn,
    isTrickTransitioning: gameState.isTrickTransitioning ?? false,
  );
});
