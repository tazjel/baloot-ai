/// connection_status_notifier.dart — Socket connection status tracking.
///
/// Port of frontend/src/hooks/useConnectionStatus.ts (27 lines).
///
/// Tracks the current socket connection state and provides
/// a reactive status for UI display (connected banner, etc.).
///
/// Uses [SocketService.onConnectionStatus] to subscribe to
/// connection state changes.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../services/socket_service.dart' as svc;

/// Tracks socket connection status for UI display.
///
/// Subscribes to [svc.SocketService] connection status events and
/// updates state reactively. Used by ConnectionBannerWidget.
class ConnectionStatusNotifier extends StateNotifier<svc.ConnectionStatus> {
  Function()? _unsubscribe;

  ConnectionStatusNotifier() : super(svc.ConnectionStatus.disconnected) {
    _subscribe();
  }

  void _subscribe() {
    _unsubscribe = svc.SocketService.instance.onConnectionStatus(
      (status, attempt) {
        if (mounted) state = status;
      },
    );
  }

  /// Whether the socket is currently connected.
  bool get isConnected => state == svc.ConnectionStatus.connected;

  /// Whether the socket is attempting to reconnect.
  bool get isReconnecting => state == svc.ConnectionStatus.reconnecting;

  @override
  void dispose() {
    _unsubscribe?.call();
    super.dispose();
  }
}

final connectionStatusProvider =
    StateNotifierProvider<ConnectionStatusNotifier, svc.ConnectionStatus>((ref) {
  return ConnectionStatusNotifier();
});
