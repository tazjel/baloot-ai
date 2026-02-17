import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:baloot_ai/state/action_dispatcher.dart';
import 'package:baloot_ai/state/providers.dart';
import 'package:baloot_ai/models/enums.dart';

void main() {
  group('ActionDispatcher — Initial State', () {
    test('starts with fast-forward disabled', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(actionDispatcherProvider);
      expect(state.isFastForwarding, false);
    });
  });

  group('ActionDispatcher — Fast Forward', () {
    test('enableFastForward sets fast-forward state and adds message', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(actionDispatcherProvider.notifier).enableFastForward();

      final dispatcherState = container.read(actionDispatcherProvider);
      expect(dispatcherState.isFastForwarding, true);

      final gameState = container.read(gameStateProvider).gameState;
      expect(gameState.isFastForwarding, true);
      expect(gameState.settings.turnDuration, closeTo(0.1, 0.01));

      // Check system message was added
      final messages = container.read(gameStateProvider).messages;
      expect(messages.any((m) => m.text.contains('Fast Forwarding')), true);
    });

    test('disableFastForward clears fast-forward state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(actionDispatcherProvider.notifier);
      notifier.enableFastForward();
      notifier.disableFastForward();

      expect(container.read(actionDispatcherProvider).isFastForwarding, false);
      expect(container.read(gameStateProvider).gameState.isFastForwarding, false);
    });
  });

  group('ActionDispatcher — Offline Actions', () {
    test('handlePlayerAction does nothing when not player 0 turn (offline)', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      // Set turn to player 2 (not human)
      container.read(gameStateProvider.notifier).updateGameState((prev) {
        return prev.copyWith(
          currentTurnIndex: 2,
          phase: GamePhase.bidding,
        );
      });

      final msgsBefore = container.read(gameStateProvider).messages.length;

      // This should be blocked (not player 0's turn)
      container.read(actionDispatcherProvider.notifier).handlePlayerAction('PASS');

      final msgsAfter = container.read(gameStateProvider).messages.length;
      expect(msgsAfter, msgsBefore); // No new messages = action was blocked
    });

    test('handlePlayerAction processes bidding action for player 0 (offline)', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      // Set up bidding phase, player 0 active and turn
      container.read(gameStateProvider.notifier).updateGameState((prev) {
        final players = List.generate(prev.players.length, (i) {
          return prev.players[i].copyWith(isActive: i == 0);
        });
        return prev.copyWith(
          currentTurnIndex: 0,
          phase: GamePhase.bidding,
          players: players,
        );
      });

      // This should trigger the real bidding logic (PASS)
      container.read(actionDispatcherProvider.notifier).handlePlayerAction('PASS');

      // Real bidding logic advances turn to next player
      final gameState = container.read(gameStateProvider).gameState;
      expect(gameState.currentTurnIndex, 1); // Next player after PASS
    });
  });

  group('ActionDispatcher — Debug Actions', () {
    test('TOGGLE_DEBUG enables debug mode (offline)', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(actionDispatcherProvider.notifier).handleDebugAction(
        'TOGGLE_DEBUG',
        payload: {'enable': true},
      );

      final settings = container.read(gameStateProvider).gameState.settings;
      expect(settings.isDebug, true);
      expect(settings.turnDuration, 99999);
    });

    test('TOGGLE_DEBUG disables debug mode (offline)', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(actionDispatcherProvider.notifier);
      notifier.handleDebugAction('TOGGLE_DEBUG', payload: {'enable': true});
      notifier.handleDebugAction('TOGGLE_DEBUG', payload: {'enable': false});

      final settings = container.read(gameStateProvider).gameState.settings;
      expect(settings.isDebug, false);
      expect(settings.turnDuration, 30);
    });
  });

  group('ActionDispatcher — Settings', () {
    test('updateSettings changes game settings (offline)', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(actionDispatcherProvider.notifier).updateSettings(
        container.read(gameStateProvider).gameState.settings.copyWith(
              turnDuration: 45,
              strictMode: false,
            ),
      );

      final settings = container.read(gameStateProvider).gameState.settings;
      expect(settings.turnDuration, 45);
      expect(settings.strictMode, false);
    });
  });

  group('ActionDispatcherState — copyWith', () {
    test('copyWith creates new instance', () {
      const original = ActionDispatcherState(isFastForwarding: false);
      final updated = original.copyWith(isFastForwarding: true);

      expect(original.isFastForwarding, false);
      expect(updated.isFastForwarding, true);
    });
  });
}
