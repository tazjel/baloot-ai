/// socket_service.dart — Socket.IO client wrapper for backend communication.
///
/// Port of frontend/src/services/SocketService.ts
///
/// Manages the persistent WebSocket connection to the Python FastAPI/Socket.IO
/// backend. Handles connection lifecycle, auto-reconnection with exponential
/// backoff, room management, and event routing.
///
/// This is a singleton — use [SocketService.instance] or the Riverpod provider.
///
/// ## Socket Events
///
/// **Emitted:**
/// - `create_room` → creates a new game room
/// - `join_room` → joins an existing room (with optional bot difficulty)
/// - `game_action` → sends player actions (PLAY, BID, SAWA, QAYD, etc.)
/// - `debug_action` → sends debug/dev actions
/// - `add_bot` → adds an AI bot to the room
///
/// **Listened:**
/// - `game_update` → server pushes updated game state
/// - `game_start` → server signals game has started
/// - `bot_speak` → bot TTS/speech bubble events
/// - Connection events: connect, disconnect, reconnect_attempt, etc.
library;
import 'dart:developer' as dev;

import 'package:socket_io_client/socket_io_client.dart' as io;

import '../models/game_state.dart';
import 'api_config.dart';

/// Connection status for the socket.
enum ConnectionStatus { connected, disconnected, reconnecting }

/// Callback type for API responses with success/error.
typedef ApiCallback = void Function(Map<String, dynamic> response);

/// Callback type for connection status changes.
typedef ConnectionStatusCallback = void Function(
    ConnectionStatus status, int? attempt);

/// Callback type for game state updates.
typedef GameStateCallback = void Function(GameState state);

/// Callback type for bot speech events.
typedef BotSpeakCallback = void Function(
    int playerIndex, String text, String emotion);

/// Singleton Socket.IO client wrapper for the Baloot AI backend.
///
/// Manages connection lifecycle, auto-reconnection, room context,
/// and all game-related socket events.
class SocketService {
  /// Singleton instance.
  static final SocketService instance = SocketService._();

  SocketService._();

  io.Socket? _socket;
  final List<ConnectionStatusCallback> _connectionCallbacks = [];
  int _reconnectAttempt = 0;
  static const int _maxReconnectAttempts = 5;

  // Room context for auto-rejoin on reconnect
  String? _activeRoomId;
  String? _activePlayerName;
  String? activeBotDifficulty;

  /// The underlying socket instance (for advanced usage).
  io.Socket? get socket => _socket;

  /// Whether the socket is currently connected.
  bool get isConnected => _socket?.connected ?? false;

  /// Connects to the backend Socket.IO server.
  ///
  /// If already connected, returns the existing socket. If disconnected,
  /// reconnects. Uses WebSocket transport with polling fallback,
  /// exponential backoff reconnection (1s → 16s max, 5 attempts).
  io.Socket connect() {
    if (_socket == null) {
      _socket = io.io(
        ApiConfig.socketUrl,
        io.OptionBuilder()
            .setTransports(['websocket', 'polling'])
            .enableReconnection()
            .setReconnectionAttempts(_maxReconnectAttempts)
            .setReconnectionDelay(1000)
            .setReconnectionDelayMax(16000)
            .build(),
      );

      _socket!.onConnect((_) {
        _reconnectAttempt = 0;
        dev.log('Connected to Game Server (id: ${_socket?.id})',
            name: 'SOCKET');
        _emitConnectionStatus(ConnectionStatus.connected);
      });

      _socket!.onConnectError((err) {
        dev.log('Connection Error: $err', name: 'SOCKET', level: 900);
      });

      _socket!.onDisconnect((reason) {
        dev.log('Disconnected: $reason', name: 'SOCKET');
        _emitConnectionStatus(ConnectionStatus.disconnected);
      });

      _socket!.on('reconnect_attempt', (attempt) {
        _reconnectAttempt = attempt is int ? attempt : 1;
        dev.log(
            'Reconnecting (attempt $_reconnectAttempt/$_maxReconnectAttempts)',
            name: 'SOCKET');
        _emitConnectionStatus(
            ConnectionStatus.reconnecting, _reconnectAttempt);
      });

      _socket!.on('reconnect', (_) {
        _reconnectAttempt = 0;
        dev.log('Reconnected successfully', name: 'SOCKET');
        _emitConnectionStatus(ConnectionStatus.connected);

        // Auto-rejoin room if we were in one before disconnect
        if (_activeRoomId != null && _activePlayerName != null) {
          dev.log('Auto-rejoining room $_activeRoomId', name: 'SOCKET');
          joinRoom(_activeRoomId!, _activePlayerName!, (res) {
            if (res['success'] == true) {
              dev.log('Auto-rejoin successful', name: 'SOCKET');
            } else {
              dev.log('Auto-rejoin failed: ${res['error']}',
                  name: 'SOCKET', level: 900);
            }
          });
        }
      });

      _socket!.on('reconnect_failed', (_) {
        dev.log(
            'Reconnection failed after $_maxReconnectAttempts attempts',
            name: 'SOCKET',
            level: 900);
        _emitConnectionStatus(ConnectionStatus.disconnected);
      });
    } else if (!_socket!.connected) {
      _socket!.connect();
    }

    return _socket!;
  }

  /// Disconnects from the backend server.
  void disconnect() {
    if (_socket != null && _socket!.connected) {
      _socket!.disconnect();
    }
  }

  /// Helper to safely parse ack response from server.
  Map<String, dynamic> _parseAck(dynamic res) {
    if (res is Map) return Map<String, dynamic>.from(res);
    if (res is List && res.isNotEmpty && res[0] is Map) {
      return Map<String, dynamic>.from(res[0] as Map);
    }
    return {'success': false, 'error': 'Invalid ack response: $res'};
  }

  /// Creates a new game room on the server.
  ///
  /// The [callback] receives `{ success: true, roomId: "..." }` on success
  /// or `{ success: false, error: "..." }` on failure.
  void createRoom(ApiCallback callback) {
    if (_socket == null) return;
    _socket!.emit('create_room', [
      {},
      (dynamic res) => callback(_parseAck(res)),
    ]);
  }

  /// Joins an existing game room.
  ///
  /// Stores the room context ([roomId], [playerName], [botDifficulty]) for
  /// automatic rejoin on reconnection.
  void joinRoom(String roomId, String playerName, ApiCallback callback,
      [String? botDifficulty]) {
    if (_socket == null) return;
    _activeRoomId = roomId;
    _activePlayerName = playerName;
    if (botDifficulty != null) activeBotDifficulty = botDifficulty;

    final payload = <String, dynamic>{
      'roomId': roomId,
      'playerName': playerName,
    };
    if (activeBotDifficulty != null) {
      payload['botDifficulty'] = activeBotDifficulty;
    }

    _socket!.emit('join_room', [
      payload,
      (dynamic res) => callback(_parseAck(res)),
    ]);
  }

  /// Sends a game action to the server.
  ///
  /// Actions include: PLAY, BID, DECLARE_PROJECT, SAWA_CLAIM,
  /// SAWA_RESPONSE, NEXT_ROUND, QAYD*, UPDATE_SETTINGS, etc.
  void sendAction(String roomId, String action,
      Map<String, dynamic> payload, [ApiCallback? callback]) {
    if (_socket == null) {
      callback?.call({'success': false, 'error': 'Socket not connected'});
      return;
    }

    _socket!.emit('game_action', [
      {
        'roomId': roomId,
        'action': action,
        'payload': payload,
      },
      (dynamic res) {
        final response = _parseAck(res);
        if (response['success'] == true) {
          dev.log('Action Success: $action', name: 'SOCKET');
        } else {
          dev.log('Action Failed: $action — ${response['error']}',
              name: 'SOCKET', level: 900);
        }
        callback?.call(response);
      },
    ]);
  }

  /// Sends a debug action (dev tools only).
  void sendDebugAction(
      String roomId, String action, Map<String, dynamic> payload) {
    if (_socket == null) return;
    _socket!.emit('debug_action', [
      {
        'roomId': roomId,
        'action': action,
        'payload': payload,
      },
      (dynamic res) {
        final response = _parseAck(res);
        if (response['success'] != true) {
          dev.log('Debug Action Failed: $action — ${response['error']}',
              name: 'SOCKET', level: 900);
        }
      },
    ]);
  }

  /// Registers a listener for `game_update` events.
  ///
  /// The callback receives the raw [GameState] from the server
  /// (before rotation). Returns an unsubscribe function.
  Function() onGameUpdate(GameStateCallback callback) {
    if (_socket == null) return () {};

    void handler(dynamic data) {
      try {
        final map = Map<String, dynamic>.from(data as Map);
        final stateJson = Map<String, dynamic>.from(map['gameState'] as Map);
        final state = GameState.fromJson(stateJson);
        dev.log(
            'Game Update: phase=${state.phase}, turn=${state.currentTurnIndex}',
            name: 'SOCKET');
        callback(state);
      } catch (e) {
        dev.log('Error parsing game_update: $e', name: 'SOCKET', level: 900);
      }
    }

    _socket!.on('game_update', handler);
    return () => _socket?.off('game_update', handler);
  }

  /// Registers a listener for `game_start` events.
  ///
  /// Returns an unsubscribe function.
  Function() onGameStart(GameStateCallback callback) {
    if (_socket == null) return () {};

    void handler(dynamic data) {
      try {
        final map = Map<String, dynamic>.from(data as Map);
        final stateJson = Map<String, dynamic>.from(map['gameState'] as Map);
        callback(GameState.fromJson(stateJson));
      } catch (e) {
        dev.log('Error parsing game_start: $e', name: 'SOCKET', level: 900);
      }
    }

    _socket!.on('game_start', handler);
    return () => _socket?.off('game_start', handler);
  }

  /// Adds an AI bot to the game room.
  void addBot(String roomId, ApiCallback callback) {
    if (_socket == null) return;
    _socket!.emit('add_bot', [
      {'roomId': roomId},
      (dynamic res) => callback(_parseAck(res)),
    ]);
  }

  /// Registers a listener for `bot_speak` events (bot TTS/speech).
  ///
  /// Returns an unsubscribe function.
  Function() onBotSpeak(BotSpeakCallback callback) {
    if (_socket == null) return () {};

    void handler(dynamic data) {
      try {
        final map = Map<String, dynamic>.from(data as Map);
        callback(
          map['playerIndex'] as int,
          map['text'] as String,
          map['emotion'] as String? ?? '',
        );
      } catch (e) {
        dev.log('Error parsing bot_speak: $e', name: 'SOCKET', level: 900);
      }
    }

    _socket!.on('bot_speak', handler);
    return () => _socket?.off('bot_speak', handler);
  }

  /// Registers a connection status change listener.
  ///
  /// Returns an unsubscribe function.
  Function() onConnectionStatus(ConnectionStatusCallback callback) {
    _connectionCallbacks.add(callback);
    return () => _connectionCallbacks.remove(callback);
  }

  void _emitConnectionStatus(ConnectionStatus status, [int? attempt]) {
    for (final cb in _connectionCallbacks) {
      cb(status, attempt);
    }
  }

  /// Clears stored room context (e.g., on logout or leave).
  void clearRoomContext() {
    _activeRoomId = null;
    _activePlayerName = null;
    activeBotDifficulty = null;
  }
}
