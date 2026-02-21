/// game_screen.dart — Main game board with full Stack architecture.
///
/// Port of frontend/src/components/Table.tsx
///
/// The game board uses a Stack with 7 layers:
/// 1. Table felt background gradient
/// 2. Player avatars at 4 positions (top, left, right, bottom)
/// 3. Game arena (center: table cards, floor card)
/// 4. Table HUD (scores, contract, round info) — top
/// 5. Hand fan (card fan) — bottom
/// 6. Action dock (bidding/playing controls) — above hand
/// 7. Overlays (toasts, speech, modals)
library;
import 'dart:developer' as dev;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/colors.dart';
import '../models/enums.dart';
import '../models/game_state.dart';
import '../services/settings_persistence.dart';
import '../state/audio/audio_notifier.dart';
import '../state/bot_turn_handler.dart';
import '../state/game_state_notifier.dart';
import '../state/providers.dart';
import '../state/ui/baloot_detection_provider.dart';
import '../state/ui/toast_notifier.dart';
import '../widgets/action_dock.dart';
import '../widgets/dispute_modal.dart';
import '../widgets/game_arena.dart';
import '../widgets/game_over_dialog.dart';
import '../widgets/hand_fan_widget.dart';
import '../widgets/heartbeat_layer.dart';
import '../widgets/hint_overlay_widget.dart';
import '../widgets/player_avatar_widget.dart';
import '../widgets/sawa_modal.dart';
import '../widgets/settings_dialog.dart';
import '../widgets/table_hud_widget.dart';
import '../widgets/connection_banner.dart';
import '../widgets/round_transition_overlay.dart';
import '../widgets/toast_overlay.dart';

/// Main game board screen.
///
/// Uses a Stack architecture with positioned layers for each
/// game board element. All player positions are relative to
/// the screen (bottom = human, top = partner, left/right = opponents).
class GameScreen extends ConsumerStatefulWidget {
  const GameScreen({super.key});

  @override
  ConsumerState<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends ConsumerState<GameScreen> {
  bool _gameStarted = false;

  @override
  void initState() {
    super.initState();
    print('[GAME] GameScreen.initState called');
    // After first frame: start game if in waiting phase, then kick off bot handler
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final gs = ref.read(gameStateProvider).gameState;
      print('[GAME] PostFrame: phase=${gs.phase}, _gameStarted=$_gameStarted, players=${gs.players.length}');
      if (gs.phase == GamePhase.waiting && !_gameStarted) {
        _gameStarted = true;
        print('[GAME] Dispatching START_GAME');
        ref.read(actionDispatcherProvider.notifier).handlePlayerAction('START_GAME');
        print('[GAME] START_GAME done, phase=${ref.read(gameStateProvider).gameState.phase}');
      }
      // Initial bot check for any state after game start
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        final gs2 = ref.read(gameStateProvider).gameState;
        print('[GAME] PostFrame2: phase=${gs2.phase}, turn=${gs2.currentTurnIndex}, isBot=${gs2.players.isNotEmpty ? gs2.players[gs2.currentTurnIndex].isBot : "?"}');
        ref.read(botTurnHandlerProvider).checkAndScheduleBotTurn();
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    print('[GAME] GameScreen.build called');

    final appState = ref.watch(gameStateProvider);
    final gameState = appState.gameState;
    final phase = gameState.phase;
    final players = gameState.players;
    final turn = gameState.currentTurnIndex;

    print('[GAME] build: phase=$phase, turn=$turn, players=${players.length}');

    // Bot turn handler — auto-play for bot players in offline mode
    final botHandler = ref.watch(botTurnHandlerProvider);
    ref.listen<AppGameState>(
      gameStateProvider,
      (previous, next) {
        botHandler.checkAndScheduleBotTurn();
      },
    );

    // DIAGNOSTIC: Minimal UI to isolate freeze
    return Scaffold(
      backgroundColor: AppColors.tableGreen,
      body: SafeArea(
        child: Column(
          children: [
            // Back button
            Align(
              alignment: Alignment.topLeft,
              child: IconButton(
                icon: const Icon(Icons.arrow_back, color: Colors.white70),
                onPressed: () => context.go('/lobby'),
              ),
            ),
            const SizedBox(height: 20),
            // Diagnostic info
            Text(
              'Game Screen OK',
              style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Text(
              'Phase: ${phase.value}',
              style: const TextStyle(color: Colors.white70, fontSize: 18),
            ),
            Text(
              'Turn: $turn (${players.length > turn ? players[turn].name : "?"})',
              style: const TextStyle(color: Colors.white70, fontSize: 18),
            ),
            Text(
              'Players: ${players.length}',
              style: const TextStyle(color: Colors.white70, fontSize: 18),
            ),
            if (players.isNotEmpty)
              Text(
                'Hand: ${players[0].hand.length} cards',
                style: const TextStyle(color: Colors.white70, fontSize: 18),
              ),
            const SizedBox(height: 20),
            // Floor card
            if (gameState.floorCard != null)
              Text(
                'Floor: ${gameState.floorCard!.rank}${gameState.floorCard!.suit.symbol}',
                style: const TextStyle(color: Colors.amber, fontSize: 22),
              ),
            const SizedBox(height: 20),
            // Simple card list for hand
            if (players.isNotEmpty)
              Wrap(
                spacing: 8,
                children: players[0].hand.map((c) => Chip(
                  label: Text('${c.rank}${c.suit.symbol}'),
                )).toList(),
              ),
            const SizedBox(height: 20),
            // Action dock placeholder
            if (phase == GamePhase.bidding) ...[
              const Text('Bidding Phase', style: TextStyle(color: Colors.amber, fontSize: 18)),
              if (turn == 0) ...[
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: () => ref.read(actionDispatcherProvider.notifier)
                          .handlePlayerAction('SUN'),
                      child: const Text('صن'),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: () => ref.read(actionDispatcherProvider.notifier)
                          .handlePlayerAction('HOKUM'),
                      child: const Text('حكم'),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: () => ref.read(actionDispatcherProvider.notifier)
                          .handlePlayerAction('PASS'),
                      child: const Text('بس'),
                    ),
                  ],
                ),
              ],
            ],
            if (phase == GamePhase.playing)
              const Text('Playing Phase', style: TextStyle(color: Colors.green, fontSize: 18)),
          ],
        ),
      ),
    );
  }

  void _recordMatch(GameState gameState, WidgetRef ref) {
    final won = gameState.matchScores.us >= 152;
    SettingsPersistence.recordMatchResult(won: won);
    SettingsPersistence.addMatchToHistory(MatchSummary(
      date: DateTime.now(),
      usScore: gameState.matchScores.us,
      themScore: gameState.matchScores.them,
      won: won,
      rounds: gameState.roundHistory.length,
      difficulty: gameState.settings.botDifficulty?.value ?? 'HARD',
    ));
  }

  void _showSettings(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => const SettingsDialog(),
    );
  }

  void _showExitConfirmation(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('مغادرة اللعبة'),
        content: const Text('هل تريد مغادرة اللعبة الحالية؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              context.go('/lobby');
            },
            child: const Text('مغادرة', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
  }
}
