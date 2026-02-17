/// playing_logic.dart — Card play and doubling handler.
///
/// Port of frontend/src/hooks/usePlayingLogic.ts (121 lines).
///
/// Handles card play actions and doubling escalation during
/// the playing phase. Only used for offline/local play — the
/// server handles this when connected.
///
/// ## Card Play Flow
/// 1. Remove card from player's hand
/// 2. Add TableCard to tableCards with player position
/// 3. If 4 cards on table → set isTrickTransitioning = true
/// 4. Otherwise advance to next player's turn
///
/// ## Doubling Escalation
/// NORMAL → DOUBLE → TRIPLE → QUADRUPLE → GAHWA
import 'dart:developer' as dev;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/card_model.dart';
import '../models/enums.dart';
import '../models/game_state.dart';
import '../models/player.dart';
import 'providers.dart';

/// Handles card play and doubling actions.
///
/// Stateless notifier (void state) — operates on the master
/// [GameStateNotifier] for all state mutations.
class PlayingLogicNotifier extends StateNotifier<void> {
  final Ref _ref;

  PlayingLogicNotifier(this._ref) : super(null);

  /// Handle a card play from a player.
  ///
  /// [playerIndex] is the seat index (0-3).
  /// [cardIndex] is the index of the card in the player's hand.
  /// [metadata] is optional additional data about the play.
  void handleCardPlay(
    int playerIndex,
    int cardIndex, {
    Map<String, dynamic>? metadata,
  }) {
    dev.log('Card Play: player=$playerIndex card=$cardIndex', name: 'PLAYING');

    final gameNotifier = _ref.read(gameStateProvider.notifier);

    gameNotifier.updateGameState((prev) {
      // Guard: valid player and card index
      if (playerIndex < 0 || playerIndex >= prev.players.length) return prev;
      final player = prev.players[playerIndex];
      if (cardIndex < 0 || cardIndex >= player.hand.length) return prev;

      final card = player.hand[cardIndex];

      // Remove card from hand
      final newHand = List<CardModel>.from(player.hand)..removeAt(cardIndex);

      // Add to table
      final newTableCard = TableCard(
        card: card,
        playedBy: player.position,
      );
      final newTable = [...prev.tableCards, newTableCard];

      // Next player index
      final nextIndex = (playerIndex + 1) % 4;

      // Update all players
      final players = List.generate(prev.players.length, (i) {
        if (i == playerIndex) {
          return prev.players[i].copyWith(
            hand: newHand,
            isActive: false,
            actionText: null,
          );
        }
        if (i == nextIndex && newTable.length < 4) {
          return prev.players[i].copyWith(isActive: true);
        }
        return prev.players[i];
      });

      // If 4 cards on table → trick transition
      if (newTable.length == 4) {
        return prev.copyWith(
          players: players,
          tableCards: newTable,
          isTrickTransitioning: true,
        );
      }

      return prev.copyWith(
        players: players,
        tableCards: newTable,
        currentTurnIndex: nextIndex,
      );
    });
  }

  /// Handle a doubling escalation action.
  ///
  /// Advances the doubling level by one step.
  /// In HOKUM mode, also locks the round (isLocked = true).
  void handleDoublingAction(int playerIndex) {
    dev.log('Doubling by player $playerIndex', name: 'PLAYING');

    final gameNotifier = _ref.read(gameStateProvider.notifier);

    gameNotifier.updateGameState((prev) {
      if (playerIndex < 0 || playerIndex >= prev.players.length) return prev;

      // Advance doubling level
      DoublingLevel newLevel = prev.doublingLevel;
      switch (prev.doublingLevel) {
        case DoublingLevel.normal:
          newLevel = DoublingLevel.double_;
          break;
        case DoublingLevel.double_:
          newLevel = DoublingLevel.triple;
          break;
        case DoublingLevel.triple:
          newLevel = DoublingLevel.quadruple;
          break;
        case DoublingLevel.quadruple:
          newLevel = DoublingLevel.gahwa;
          break;
        case DoublingLevel.gahwa:
          break; // Max level reached
      }

      gameNotifier.addSystemMessage(
        '${prev.players[playerIndex].name} رفع المشاريع',
      );

      // In HOKUM, doubling locks the round
      final isHokum = prev.bid.type == GameMode.hokum;

      return prev.copyWith(
        doublingLevel: newLevel,
        isLocked: isHokum ? true : prev.isLocked,
      );
    });
  }
}
