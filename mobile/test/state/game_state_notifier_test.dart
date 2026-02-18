import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:baloot_ai/state/providers.dart';
import 'package:baloot_ai/models/enums.dart';
import 'package:baloot_ai/models/game_settings.dart';

void main() {
  group('GameStateNotifier — Initialization', () {
    test('initial state has 4 players in correct positions', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final appState = container.read(gameStateProvider);
      final gs = appState.gameState;

      expect(gs.players.length, 4);
      expect(gs.players[0].position, PlayerPosition.bottom);
      expect(gs.players[1].position, PlayerPosition.right);
      expect(gs.players[2].position, PlayerPosition.top);
      expect(gs.players[3].position, PlayerPosition.left);
    });

    test('initial state is in Waiting phase', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final appState = container.read(gameStateProvider);
      expect(appState.gameState.phase, GamePhase.waiting);
    });

    test('initial messages list is empty', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final appState = container.read(gameStateProvider);
      expect(appState.messages, isEmpty);
    });

    test('dealer is player 3 (index 3)', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final gs = container.read(gameStateProvider).gameState;
      expect(gs.dealerIndex, 3);
      expect(gs.players[3].isDealer, true);
    });

    test('player 0 is human, others are bots', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final gs = container.read(gameStateProvider).gameState;
      expect(gs.players[0].isBot, false);
      expect(gs.players[1].isBot, true);
      expect(gs.players[2].isBot, true);
      expect(gs.players[3].isBot, true);
    });
  });

  group('GameStateNotifier — State Mutation', () {
    test('setGameState replaces game state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(gameStateProvider.notifier);

      notifier.setGameState(
        notifier.gameState.copyWith(phase: GamePhase.bidding),
      );

      expect(
        container.read(gameStateProvider).gameState.phase,
        GamePhase.bidding,
      );
    });

    test('setGameStateFromServer preserves local settings', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(gameStateProvider.notifier);

      // Set custom local settings
      notifier.updateSettings(
        const GameSettings(turnDuration: 99, showHints: true),
      );

      // Simulate server update (settings would be default from server)
      final serverState = notifier.gameState.copyWith(
        phase: GamePhase.playing,
        settings: const GameSettings(turnDuration: 15), // Server default
      );
      notifier.setGameStateFromServer(serverState);

      final gs = container.read(gameStateProvider).gameState;
      expect(gs.phase, GamePhase.playing); // Server value applied
      expect(gs.settings.turnDuration, 99); // Local settings preserved
      expect(gs.settings.showHints, true); // Local settings preserved
    });

    test('updateGameState applies mutation function', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(gameStateProvider.notifier);

      notifier.updateGameState((prev) {
        return prev.copyWith(
          currentTurnIndex: 2,
          phase: GamePhase.playing,
        );
      });

      final gs = container.read(gameStateProvider).gameState;
      expect(gs.currentTurnIndex, 2);
      expect(gs.phase, GamePhase.playing);
    });
  });

  group('GameStateNotifier — System Messages', () {
    test('addSystemMessage appends to messages list', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(gameStateProvider.notifier);

      notifier.addSystemMessage('بدأت الجولة');
      notifier.addSystemMessage('دورك');

      final messages = container.read(gameStateProvider).messages;
      expect(messages.length, 2);
      expect(messages[0].text, 'بدأت الجولة');
      expect(messages[1].text, 'دورك');
      expect(messages[0].sender, 'النظام');
    });
  });

  group('GameStateNotifier — Settings Management', () {
    test('updateSettings replaces entire settings object', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(gameStateProvider.notifier);

      notifier.updateSettings(
        const GameSettings(
          turnDuration: 30,
          strictMode: false,
          soundEnabled: false,
        ),
      );

      final settings = container.read(gameStateProvider).gameState.settings;
      expect(settings.turnDuration, 30);
      expect(settings.strictMode, false);
      expect(settings.soundEnabled, false);
    });

    test('mergeSettings only changes specified fields', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(gameStateProvider.notifier);

      // Default: turnDuration=15, strictMode=true, soundEnabled=true
      notifier.mergeSettings(turnDuration: 60);

      final settings = container.read(gameStateProvider).gameState.settings;
      expect(settings.turnDuration, 60); // Changed
      expect(settings.strictMode, true); // Preserved
      expect(settings.soundEnabled, true); // Preserved
    });
  });

  group('GameStateNotifier — Reset', () {
    test('reset returns to initial state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(gameStateProvider.notifier);

      // Mutate state
      notifier.addSystemMessage('test');
      notifier.updateGameState((prev) => prev.copyWith(phase: GamePhase.playing));
      notifier.setIsCuttingDeck(true);

      // Reset
      notifier.reset();

      final appState = container.read(gameStateProvider);
      expect(appState.gameState.phase, GamePhase.waiting);
      expect(appState.messages, isEmpty);
      expect(appState.isCuttingDeck, false);
    });
  });
}
