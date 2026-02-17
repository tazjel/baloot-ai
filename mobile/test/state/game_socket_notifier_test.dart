import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:baloot_ai/state/game_socket_notifier.dart';
import 'package:baloot_ai/state/providers.dart';

void main() {
  group('GameSocketNotifier — Initial State', () {
    test('starts with no room and index 0', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final socketState = container.read(gameSocketProvider);
      expect(socketState.roomId, isNull);
      expect(socketState.myIndex, 0);
      expect(socketState.isSendingAction, false);
    });
  });

  group('SocketState — copyWith', () {
    test('copyWith creates new instance with updated fields', () {
      const original = SocketState(roomId: 'room1', myIndex: 0);
      final updated = original.copyWith(myIndex: 2);

      expect(updated.roomId, 'room1');
      expect(updated.myIndex, 2);
    });

    test('copyWith preserves unchanged fields', () {
      const original = SocketState(roomId: 'abc', myIndex: 3, isSendingAction: true);
      final updated = original.copyWith(roomId: 'xyz');

      expect(updated.roomId, 'xyz');
      expect(updated.myIndex, 3);
      expect(updated.isSendingAction, true);
    });
  });

  group('GameSocketNotifier — Action Blocking', () {
    test('sendAction blocks when not in a room', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(gameSocketProvider.notifier);

      // Should not throw, just log a warning
      notifier.sendAction('PLAY', payload: {'cardIndex': 0});

      // State should remain unchanged (no isSendingAction toggle)
      expect(container.read(gameSocketProvider).isSendingAction, false);
    });
  });

  group('GameSocketNotifier — Room Management', () {
    test('leaveRoom resets socket state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(gameSocketProvider.notifier);
      notifier.leaveRoom();

      final state = container.read(gameSocketProvider);
      expect(state.roomId, isNull);
      expect(state.myIndex, 0);
      expect(state.isSendingAction, false);
    });
  });
}
