/// action_dispatcher.dart — Central action routing facade.
///
/// Port of frontend/src/hooks/useActionDispatcher.ts (124 lines).
///
/// Routes all player actions to the appropriate handler based on game phase
/// and connection state:
/// - **Connected (roomId != null)**: Forward action to server via socket
/// - **Offline (roomId == null)**: Handle locally via bidding/playing logic
///
/// ## Fast Forward Mode
/// When enabled, auto-plays the first valid move every 150ms. Used for
/// testing and debugging to rapidly advance through a game.
///
/// ## Action Types
/// - Bidding: SUN, HOKUM, PASS, ASHKAL
/// - Playing: PLAY
/// - Doubling: DOUBLE
/// - Qayd: QAYD_START, QAYD_SELECT_VIOLATION, etc.
/// - Settings: UPDATE_SETTINGS
/// - Special: NEXT_ROUND, DECLARE_PROJECT, SAWA_CLAIM, SAWA_RESPONSE
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/enums.dart';
import '../models/game_settings.dart';
import '../models/game_state.dart';
import '../utils/trick_utils.dart';
import 'providers.dart';

/// Manages fast-forward state for auto-play mode.
class ActionDispatcherState {
  final bool isFastForwarding;

  const ActionDispatcherState({this.isFastForwarding = false});

  ActionDispatcherState copyWith({bool? isFastForwarding}) {
    return ActionDispatcherState(
      isFastForwarding: isFastForwarding ?? this.isFastForwarding,
    );
  }
}

/// Central action dispatcher.
///
/// Routes player actions to the server (when connected) or to local
/// handlers (when offline). Also manages fast-forward auto-play mode.
class ActionDispatcher extends StateNotifier<ActionDispatcherState> {
  final Ref _ref;

  /// Timer for fast-forward auto-play interval.
  Timer? _fastForwardTimer;

  ActionDispatcher(this._ref) : super(const ActionDispatcherState());

  // =========================================================================
  // Main Action Dispatch
  // =========================================================================

  /// Handle a player action by routing to server or local logic.
  ///
  /// When connected to a server room, all actions are forwarded via the
  /// socket. When offline, actions are handled locally for the human
  /// player (index 0) only.
  void handlePlayerAction(String action, {Map<String, dynamic>? payload}) {
    final socketState = _ref.read(gameSocketProvider);
    final gameNotifier = _ref.read(gameStateProvider.notifier);
    final gameState = gameNotifier.gameState;

    // Block duplicate actions (except Qayd escape hatch)
    if (socketState.isSendingAction && !action.startsWith('QAYD')) return;

    print('[DISPATCHER] Player Action: $action');

    // If connected to server, forward via socket
    if (socketState.roomId != null) {
      _ref.read(gameSocketProvider.notifier).sendAction(
        action,
        payload: payload,
        onComplete: (res) {
          if (res['success'] != true) {
            gameNotifier
                .addSystemMessage('Action Failed: ${res['error'] ?? 'Unknown'}');
            // Could play error sound here via audio notifier
          }
        },
      );
      return;
    }

    // --- OFFLINE LOCAL LOGIC ---

    // START_GAME: deal cards and begin first round
    if (action == 'START_GAME') {
      _ref.read(roundManagerProvider.notifier).startNewRound(
            nextDealerIndex: gameState.dealerIndex,
          );
      return;
    }

    // Only allow human player actions (index 0)
    if (gameState.currentTurnIndex != 0) return;

    if (gameState.phase == GamePhase.bidding) {
      _ref.read(biddingLogicProvider.notifier).handleBiddingAction(
            0,
            action,
            payload: payload,
          );
    } else if (gameState.phase == GamePhase.playing && action == 'PLAY') {
      final cardIndex = payload?['cardIndex'] as int?;
      if (cardIndex == null) return;

      // Validation (permissive — Qayd allows illegal moves)
      final card = gameState.players[0].hand[cardIndex];
      final trumpSuit = gameState.bid.type == GameMode.hokum
          ? (gameState.bid.suit ?? gameState.floorCard?.suit)
          : null;
      final mode = gameState.bid.type == GameMode.sun
          ? GameMode.sun
          : GameMode.hokum;

      if (gameState.settings.strictMode &&
          !isValidMove(
            card: card,
            hand: gameState.players[0].hand,
            tableCards: gameState.tableCards,
            mode: mode,
            trumpSuit: trumpSuit,
            isLocked: gameState.isLocked,
          )) {
        gameNotifier.addSystemMessage('حركة غير صالحة!');
        return;
      }

      _ref.read(playingLogicProvider.notifier).handleCardPlay(
            0,
            cardIndex,
            metadata: payload?['metadata'] as Map<String, dynamic>?,
          );
    } else if (action == 'DOUBLE') {
      _ref.read(playingLogicProvider.notifier).handleDoublingAction(0);
    }
  }

  // =========================================================================
  // Fast Forward
  // =========================================================================

  /// Enable fast-forward mode: auto-plays the first valid move at 150ms.
  void enableFastForward() {
    final gameNotifier = _ref.read(gameStateProvider.notifier);
    gameNotifier.addSystemMessage('>>> (Fast Forwarding...)');
    gameNotifier.updateGameState((prev) {
      return prev.copyWith(
        isFastForwarding: true,
        settings: prev.settings.copyWith(turnDuration: 0.1),
      );
    });
    state = state.copyWith(isFastForwarding: true);
  }

  /// Disable fast-forward mode.
  void disableFastForward() {
    _fastForwardTimer?.cancel();
    _fastForwardTimer = null;
    state = state.copyWith(isFastForwarding: false);
    _ref.read(gameStateProvider.notifier).updateGameState((prev) {
      return prev.copyWith(isFastForwarding: false);
    });
  }

  /// Called periodically when fast-forward is active.
  ///
  /// Finds the first valid card and plays it automatically.
  void _fastForwardTick() {
    final gameState = _ref.read(gameStateProvider.notifier).gameState;

    if (!state.isFastForwarding ||
        gameState.phase != GamePhase.playing) return;

    // Don't play during transitions
    if (gameState.isTrickTransitioning == true ||
        gameState.isProjectRevealing == true ||
        gameState.isRoundTransitioning == true) return;

    final idx = gameState.currentTurnIndex;
    final hand = gameState.players[idx].hand;
    if (hand.isEmpty) return;

    final trumpSuit = gameState.bid.type == GameMode.hokum
        ? (gameState.bid.suit ?? gameState.floorCard?.suit)
        : null;
    final mode = gameState.bid.type == GameMode.sun
        ? GameMode.sun
        : GameMode.hokum;

    // Find first valid card
    int validIndex = -1;
    for (int i = 0; i < hand.length; i++) {
      if (isValidMove(
        card: hand[i],
        hand: hand,
        tableCards: gameState.tableCards,
        mode: mode,
        trumpSuit: trumpSuit,
        isLocked: gameState.isLocked,
      )) {
        validIndex = i;
        break;
      }
    }

    if (validIndex >= 0) {
      _ref.read(playingLogicProvider.notifier).handleCardPlay(
            idx,
            validIndex,
          );
    }
  }

  // =========================================================================
  // Debug & Settings
  // =========================================================================

  /// Send a debug action (dev tools only).
  void handleDebugAction(String action, {Map<String, dynamic>? payload}) {
    final socketState = _ref.read(gameSocketProvider);

    if (socketState.roomId != null) {
      _ref.read(gameSocketProvider.notifier).sendDebugAction(
            action,
            payload: payload,
          );
    } else if (action == 'TOGGLE_DEBUG') {
      final enable = payload?['enable'] as bool? ?? false;
      _ref.read(gameStateProvider.notifier).mergeSettings(
            isDebug: enable,
            turnDuration: enable ? 99999 : 30,
          );
      _ref
          .read(gameStateProvider.notifier)
          .addSystemMessage('Debug Mode: ${enable ? 'ON' : 'OFF'}');
    }
  }

  /// Update game settings locally and sync with server if connected.
  void updateSettings(GameSettings newSettings) {
    _ref.read(gameStateProvider.notifier).updateSettings(newSettings);

    final socketState = _ref.read(gameSocketProvider);
    if (socketState.roomId != null) {
      _ref.read(gameSocketProvider.notifier).sendAction(
        'UPDATE_SETTINGS',
        payload: newSettings.toJson(),
      );
    }
  }

  // =========================================================================
  // Lifecycle
  // =========================================================================

  @override
  void dispose() {
    _fastForwardTimer?.cancel();
    super.dispose();
  }
}
