/// game_socket_notifier.dart — Socket.IO ↔ game state bridge.
///
/// Port of frontend/src/hooks/useGameSocket.ts (298 lines).
///
/// This notifier manages the lifecycle of the socket connection and bridges
/// server events into Riverpod state updates. It handles:
/// - Room creation, joining, and context management
/// - Action dispatching with optimistic locking (anti-duplicate)
/// - Game state rotation (server absolute → client relative perspective)
/// - Socket event listeners for `game_update` and `game_start`
///
/// ## Anti-Duplication
/// All actions except Qayd wizard steps are blocked while a previous action
/// is in-flight. This prevents double-tap issues on mobile.
///
/// ## State Rotation
/// The server uses absolute seat indices (0–3). This notifier applies
/// [rotateGameState] before forwarding to [GameStateNotifier], so the local
/// player is always at index 0 (Bottom position).
import 'dart:developer' as dev;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/game_state.dart';
import '../services/socket_service.dart';
import '../services/state_rotation.dart';
import 'providers.dart';

/// Connection and room state for the socket layer.
class SocketState {
  final String? roomId;
  final int myIndex;
  final bool isSendingAction;

  const SocketState({
    this.roomId,
    this.myIndex = 0,
    this.isSendingAction = false,
  });

  SocketState copyWith({
    String? roomId,
    int? myIndex,
    bool? isSendingAction,
  }) {
    return SocketState(
      roomId: roomId ?? this.roomId,
      myIndex: myIndex ?? this.myIndex,
      isSendingAction: isSendingAction ?? this.isSendingAction,
    );
  }
}

/// Manages socket connection, room membership, and server communication.
///
/// Listens to socket events and routes game state updates through
/// [rotateGameState] before forwarding to the master [GameStateNotifier].
class GameSocketNotifier extends StateNotifier<SocketState> {
  final Ref _ref;
  final SocketService _socketService = SocketService.instance;

  /// Unsubscribe callbacks for socket event listeners.
  Function()? _gameUpdateCleanup;
  Function()? _gameStartCleanup;

  GameSocketNotifier(this._ref) : super(const SocketState());

  // =========================================================================
  // Connection
  // =========================================================================

  /// Ensure the socket is connected.
  void ensureConnected() {
    _socketService.connect();
  }

  // =========================================================================
  // Room Management
  // =========================================================================

  /// Create a new game room.
  ///
  /// Calls the server's `create_room` event. On success, stores the roomId
  /// and returns it via [onComplete].
  void createRoom({
    required void Function(String roomId) onSuccess,
    void Function(String error)? onError,
  }) {
    ensureConnected();
    _socketService.createRoom((res) {
      if (res['success'] == true) {
        final roomId = res['roomId'] as String;
        state = state.copyWith(roomId: roomId);
        dev.log('Room Created: $roomId', name: 'SOCKET_NOTIFIER');
        onSuccess(roomId);
      } else {
        final error = res['error'] as String? ?? 'Unknown error';
        dev.log('Create Room Failed: $error', name: 'SOCKET_NOTIFIER');
        onError?.call(error);
      }
    });
  }

  /// Join an existing game room and start listening for events.
  ///
  /// After joining, subscribes to `game_update` and `game_start` events.
  /// The initial game state is rotated to the client's perspective.
  void joinGame({
    required String roomId,
    required String playerName,
    required int myIndex,
    String? botDifficulty,
    void Function()? onSuccess,
    void Function(String error)? onError,
  }) {
    ensureConnected();

    _socketService.joinRoom(roomId, playerName, (res) {
      if (res['success'] == true) {
        // Server may assign playerIndex; use it if available, else fallback
        final serverIndex = res['playerIndex'] as int?;
        final actualIndex = serverIndex ?? (myIndex >= 0 ? myIndex : 0);
        state = state.copyWith(roomId: roomId, myIndex: actualIndex);
        dev.log('Joined Room: $roomId as player $actualIndex', name: 'SOCKET_NOTIFIER');

        // Subscribe to game events
        _subscribeToGameEvents();

        // If the response includes initial state, apply it
        if (res.containsKey('gameState') && res['gameState'] is Map) {
          final serverState = GameState.fromJson(
            Map<String, dynamic>.from(res['gameState'] as Map),
          );
          _applyServerState(serverState);
        }

        onSuccess?.call();
      } else {
        final error = res['error'] as String? ?? 'Unknown error';
        dev.log('Join Room Failed: $error', name: 'SOCKET_NOTIFIER');
        onError?.call(error);
      }
    }, botDifficulty);
  }

  /// Add an AI bot to the current room.
  void addBot({void Function(bool success, String? error)? onComplete}) {
    final roomId = state.roomId;
    if (roomId == null) return;

    _socketService.addBot(roomId, (res) {
      final success = res['success'] == true;
      final error = success ? null : (res['error'] as String? ?? 'Unknown error');
      onComplete?.call(success, error);
    });
  }

  // =========================================================================
  // Action Dispatching
  // =========================================================================

  /// Send a game action to the server.
  ///
  /// Routes the action to the appropriate server event based on [action] type.
  /// Blocks duplicate actions (except Qayd wizard steps) using [isSendingAction].
  ///
  /// Actions: PLAY, SUN, HOKUM, PASS, ASHKAL, DECLARE_PROJECT, SAWA_CLAIM,
  /// SAWA_RESPONSE, NEXT_ROUND, QAYD*, DOUBLE, UPDATE_SETTINGS.
  void sendAction(
    String action, {
    Map<String, dynamic>? payload,
    void Function(Map<String, dynamic> response)? onComplete,
  }) {
    final roomId = state.roomId;
    if (roomId == null) {
      dev.log('Cannot send action — not in a room', name: 'SOCKET_NOTIFIER');
      return;
    }

    // Block duplicate actions (except Qayd multi-step wizard)
    if (state.isSendingAction && !action.startsWith('QAYD')) {
      dev.log('Action blocked — already sending', name: 'SOCKET_NOTIFIER');
      return;
    }

    state = state.copyWith(isSendingAction: true);

    void handleResponse(Map<String, dynamic> res) {
      if (mounted) {
        state = state.copyWith(isSendingAction: false);
      }
      if (res['success'] == true) {
        dev.log('Action Success: $action', name: 'SOCKET_NOTIFIER');
      } else {
        dev.log('Action Failed: $action — ${res['error']}',
            name: 'SOCKET_NOTIFIER');
      }
      onComplete?.call(res);
    }

    // Route action to appropriate server event
    final actionPayload = payload ?? {};

    if (action == 'PLAY') {
      _socketService.sendAction(roomId, 'PLAY', actionPayload, handleResponse);
    } else if (['SUN', 'HOKUM', 'PASS', 'ASHKAL'].contains(action)) {
      _socketService.sendAction(
        roomId,
        'BID',
        {'action': action, 'suit': actionPayload['suit']},
        handleResponse,
      );
    } else if (action == 'DECLARE_PROJECT') {
      _socketService.sendAction(roomId, 'DECLARE_PROJECT', actionPayload, handleResponse);
    } else if (action == 'SAWA_CLAIM') {
      _socketService.sendAction(roomId, 'SAWA_CLAIM', {}, handleResponse);
    } else if (action == 'SAWA_RESPONSE') {
      _socketService.sendAction(roomId, 'SAWA_RESPONSE', actionPayload, handleResponse);
    } else if (action == 'NEXT_ROUND') {
      _socketService.sendAction(roomId, 'NEXT_ROUND', {}, handleResponse);
    } else if (action.startsWith('QAYD')) {
      _socketService.sendAction(roomId, action, actionPayload, handleResponse);
    } else if (action == 'UPDATE_SETTINGS') {
      _socketService.sendAction(roomId, 'UPDATE_SETTINGS', actionPayload, handleResponse);
    } else if (action == 'DOUBLE') {
      _socketService.sendAction(roomId, 'DOUBLE', {}, handleResponse);
    } else if (action == 'AKKA') {
      _socketService.sendAction(roomId, 'AKKA', actionPayload, handleResponse);
    } else if (action == 'KAWESH') {
      _socketService.sendAction(roomId, 'KAWESH', {}, handleResponse);
    } else {
      dev.log('Unhandled action: $action', name: 'SOCKET_NOTIFIER');
      state = state.copyWith(isSendingAction: false);
    }
  }

  /// Send a debug action to the server (dev tools only).
  void sendDebugAction(String action, {Map<String, dynamic>? payload}) {
    final roomId = state.roomId;
    if (roomId == null) return;
    _socketService.sendDebugAction(roomId, action, payload ?? {});
  }

  // =========================================================================
  // Event Subscriptions
  // =========================================================================

  /// Subscribe to `game_update` and `game_start` socket events.
  void _subscribeToGameEvents() {
    // Clean up any existing listeners
    _gameUpdateCleanup?.call();
    _gameStartCleanup?.call();

    _gameUpdateCleanup = _socketService.onGameUpdate((serverState) {
      if (!mounted) return;
      _applyServerState(serverState);
    });

    _gameStartCleanup = _socketService.onGameStart((serverState) {
      if (!mounted) return;
      dev.log('Game Start received', name: 'SOCKET_NOTIFIER');
      _applyServerState(serverState);
    });
  }

  /// Rotate server state and forward to [GameStateNotifier].
  void _applyServerState(GameState serverState) {
    final rotated = rotateGameState(serverState, state.myIndex);
    _ref.read(gameStateProvider.notifier).setGameStateFromServer(rotated);
  }

  // =========================================================================
  // Room Context
  // =========================================================================

  /// Leave the current room and clean up.
  void leaveRoom() {
    _gameUpdateCleanup?.call();
    _gameStartCleanup?.call();
    _gameUpdateCleanup = null;
    _gameStartCleanup = null;
    _socketService.clearRoomContext();
    state = const SocketState();
  }

  // =========================================================================
  // Lifecycle
  // =========================================================================

  @override
  void dispose() {
    _gameUpdateCleanup?.call();
    _gameStartCleanup?.call();
    super.dispose();
  }
}
