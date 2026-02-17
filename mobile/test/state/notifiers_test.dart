/// Tests for UI notifiers: ToastNotifier, ReplayNotifier.
///
/// AudioNotifier tests will be added by Gemini when audio_notifier.dart is created.
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:baloot_ai/state/ui/toast_notifier.dart';
import 'package:baloot_ai/state/ui/replay_notifier.dart';
import 'package:baloot_ai/models/game_state.dart';
import 'package:baloot_ai/models/enums.dart';

void main() {
  group('ToastNotifier', () {
    late ToastNotifier notifier;

    setUp(() {
      notifier = ToastNotifier();
    });

    test('adds toast messages', () {
      notifier.show('Test Message');
      expect(notifier.state.length, 1);
      expect(notifier.state.first.message, 'Test Message');
    });

    test('removes toast messages', () {
      notifier.show('Test Message');
      final id = notifier.state.first.id;
      notifier.remove(id);
      expect(notifier.state.isEmpty, true);
    });

    test('limits to 3 messages', () {
      notifier.show('1');
      notifier.show('2');
      notifier.show('3');
      notifier.show('4');
      expect(notifier.state.length, 3);
      expect(notifier.state.last.message, '4');
      expect(notifier.state.first.message, '2'); // '1' should be removed
    });

    test('clear removes all toasts', () {
      notifier.show('A');
      notifier.show('B');
      notifier.clear();
      expect(notifier.state, isEmpty);
    });

    test('toast has correct type', () {
      notifier.show('Error!', type: ToastType.error);
      expect(notifier.state.first.type, ToastType.error);
    });
  });

  group('ReplayNotifier', () {
    late ReplayNotifier notifier;

    setUp(() {
      notifier = ReplayNotifier();
    });

    test('starts inactive', () {
      expect(notifier.state.isActive, false);
      expect(notifier.state.isPlaying, false);
    });

    test('startReplay activates with history', () {
      final history = [GameState.initial(), GameState.initial()];
      notifier.startReplay(history);

      expect(notifier.state.isActive, true);
      expect(notifier.state.totalSteps, 2);
      expect(notifier.state.currentIndex, 0);
    });

    test('startReplay with empty history does nothing', () {
      notifier.startReplay([]);
      expect(notifier.state.isActive, false);
    });

    test('next advances current index', () {
      final history = [
        GameState.initial(),
        GameState.initial(),
        GameState.initial(),
      ];
      notifier.startReplay(history);
      notifier.next();
      expect(notifier.state.currentIndex, 1);
    });

    test('next does not go past end', () {
      final history = [GameState.initial(), GameState.initial()];
      notifier.startReplay(history);
      notifier.next();
      notifier.next(); // Should stop at index 1 (last)
      expect(notifier.state.currentIndex, 1);
    });

    test('previous goes back', () {
      final history = [
        GameState.initial(),
        GameState.initial(),
        GameState.initial(),
      ];
      notifier.startReplay(history);
      notifier.next();
      notifier.next();
      notifier.previous();
      expect(notifier.state.currentIndex, 1);
    });

    test('previous does not go below 0', () {
      final history = [GameState.initial()];
      notifier.startReplay(history);
      notifier.previous();
      expect(notifier.state.currentIndex, 0);
    });

    test('jumpTo sets specific index', () {
      final history = List.generate(5, (_) => GameState.initial());
      notifier.startReplay(history);
      notifier.jumpTo(3);
      expect(notifier.state.currentIndex, 3);
    });

    test('jumpTo ignores invalid indices', () {
      final history = List.generate(3, (_) => GameState.initial());
      notifier.startReplay(history);
      notifier.jumpTo(10); // Out of range
      expect(notifier.state.currentIndex, 0);
      notifier.jumpTo(-1); // Negative
      expect(notifier.state.currentIndex, 0);
    });

    test('exitReplay resets state', () {
      final history = [GameState.initial(), GameState.initial()];
      notifier.startReplay(history);
      notifier.next();
      notifier.exitReplay();
      expect(notifier.state.isActive, false);
      expect(notifier.state.isPlaying, false);
    });

    test('setSpeed updates playback speed', () {
      final history = [GameState.initial()];
      notifier.startReplay(history);
      notifier.setSpeed(2.0);
      expect(notifier.state.playbackSpeed, 2.0);
    });

    test('currentState returns correct GameState', () {
      final states = [
        GameState.initial().copyWith(currentTurnIndex: 0),
        GameState.initial().copyWith(currentTurnIndex: 1),
      ];
      notifier.startReplay(states);
      expect(notifier.state.currentState?.currentTurnIndex, 0);
      notifier.next();
      expect(notifier.state.currentState?.currentTurnIndex, 1);
    });
  });

  group('ReplayState — copyWith', () {
    test('copyWith preserves unchanged fields', () {
      const original = ReplayState(
        isActive: true,
        isPlaying: false,
        currentIndex: 5,
        totalSteps: 10,
      );
      final updated = original.copyWith(isPlaying: true);
      expect(updated.isActive, true);
      expect(updated.isPlaying, true);
      expect(updated.currentIndex, 5);
      expect(updated.totalSteps, 10);
    });
  });
}
