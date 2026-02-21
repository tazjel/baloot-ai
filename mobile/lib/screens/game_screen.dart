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
///
/// Converted from ConsumerWidget to ConsumerStatefulWidget to support:
/// - Auto-starting the game when navigating from lobby (START_GAME dispatch)
/// - Bot turn scheduling via [BotTurnHandler]
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
    // After first frame: start game if in waiting phase, then wire bot handler.
    // Using postFrameCallback ensures providers are fully initialized.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _maybeStartGame();
      _wireBotListener();
    });
  }

  /// Start the game if still in waiting phase (offline mode).
  void _maybeStartGame() {
    final gs = ref.read(gameStateProvider).gameState;
    if (gs.phase == GamePhase.waiting && !_gameStarted) {
      _gameStarted = true;
      ref.read(actionDispatcherProvider.notifier).handlePlayerAction('START_GAME');
    }
  }

  /// Wire up a one-time listener that triggers bot turns on every state change.
  /// Done in initState (via postFrameCallback) rather than build() to avoid
  /// re-registering the listener on every rebuild.
  void _wireBotListener() {
    // Initial bot check after game start
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(botTurnHandlerProvider).checkAndScheduleBotTurn();
    });

    // Ongoing: check for bot turns whenever game state changes
    ref.listenManual<AppGameState>(
      gameStateProvider,
      (previous, next) {
        ref.read(botTurnHandlerProvider).checkAndScheduleBotTurn();
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    // Initialize audio notifier (watches game state internally)
    ref.watch(audioNotifierProvider);

    // Baloot detection — show toast when K+Q of trump detected
    ref.listen<BalootDetectionState>(
      balootDetectionProvider,
      (previous, next) {
        if (next.hasBaloot && !(previous?.hasBaloot ?? false)) {
          ref.read(toastProvider.notifier).show(
            'بلوت! لديك الملك والملكة ${next.trumpSuit?.symbol ?? ''}',
            type: ToastType.baloot,
            duration: const Duration(seconds: 4),
          );
        }
      },
    );

    final appState = ref.watch(gameStateProvider);
    final gameState = appState.gameState;
    final players = gameState.players;
    final phase = gameState.phase;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(color: AppColors.tableGreen),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final w = constraints.maxWidth;
              final h = constraints.maxHeight;

              return Stack(
                children: [
                  // === Layer 0: Table felt background ===
                  const Positioned.fill(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: RadialGradient(
                          center: Alignment.center,
                          radius: 1.2,
                          colors: [
                            AppColors.tableGreenLight,
                            AppColors.tableGreen,
                            AppColors.tableGreenDark,
                          ],
                        ),
                      ),
                    ),
                  ),

                  // === Layer 1: Top player avatar (partner, index 2) ===
                  if (players.length > 2)
                    Positioned(
                      top: 44,
                      left: 0,
                      right: 0,
                      child: Center(
                        child: PlayerAvatarWidget(
                          player: players[2],
                          index: 2,
                          isCurrentTurn: gameState.currentTurnIndex == 2,
                          scale: 0.85,
                        ),
                      ),
                    ),

                  // === Layer 1: Left player avatar (opponent, index 3) ===
                  if (players.length > 3)
                    Positioned(
                      top: h * 0.35,
                      left: 8,
                      child: PlayerAvatarWidget(
                        player: players[3],
                        index: 3,
                        isCurrentTurn: gameState.currentTurnIndex == 3,
                        scale: 0.8,
                      ),
                    ),

                  // === Layer 1: Right player avatar (opponent, index 1) ===
                  if (players.length > 1)
                    Positioned(
                      top: h * 0.35,
                      right: 8,
                      child: PlayerAvatarWidget(
                        player: players[1],
                        index: 1,
                        isCurrentTurn: gameState.currentTurnIndex == 1,
                        scale: 0.8,
                      ),
                    ),

                  // === Layer 1: Bottom player avatar (human, index 0) ===
                  if (players.isNotEmpty)
                    Positioned(
                      bottom: h * 0.26,
                      left: 0,
                      right: 0,
                      child: Center(
                        child: PlayerAvatarWidget(
                          player: players[0],
                          index: 0,
                          isCurrentTurn: gameState.currentTurnIndex == 0,
                          scale: 0.85,
                        ),
                      ),
                    ),

                  // === Layer 2: Game arena (center play area) ===
                  Positioned(
                    top: h * 0.18,
                    left: w * 0.15,
                    right: w * 0.15,
                    bottom: h * 0.38,
                    child: const GameArena(),
                  ),

                  // === Layer 3: Table HUD (scores + contract) ===
                  const Positioned(
                    top: 0,
                    left: 0,
                    right: 0,
                    child: TableHudWidget(),
                  ),

                  // === Layer 4: Hand fan (bottom card fan) ===
                  Positioned(
                    bottom: phase == GamePhase.waiting ? 16 : 56,
                    left: 8,
                    right: 8,
                    child: const HandFanWidget(),
                  ),

                  // === Layer 5: Action dock (bidding/playing controls) ===
                  const Positioned(
                    bottom: 0,
                    left: 0,
                    right: 0,
                    child: ActionDock(),
                  ),

                  // === Layer 6: Overlays ===
                  const HeartbeatLayer(),
                  const HintOverlayWidget(),
                  const ToastOverlay(),
                  const RoundTransitionOverlay(),

                  // === Layer 7: Modal overlays (Qayd + Sawa) ===
                  const Positioned.fill(child: SawaModal()),
                  const Positioned.fill(child: DisputeModal()),

                  // === Layer 8: Connection banner (top) ===
                  const Positioned(
                    top: 0,
                    left: 0,
                    right: 0,
                    child: ConnectionBanner(),
                  ),

                  // === Layer 9: Game Over overlay ===
                  if (phase == GamePhase.gameOver)
                    Positioned.fill(
                      child: GameOverDialog(
                        matchScores: gameState.matchScores,
                        roundHistory: gameState.roundHistory,
                        onPlayAgain: () {
                          _recordMatch(gameState);
                          ref.read(gameStateProvider.notifier).reset();
                          _gameStarted = false;
                          // Re-start after reset
                          WidgetsBinding.instance.addPostFrameCallback((_) {
                            if (!mounted) return;
                            _maybeStartGame();
                          });
                        },
                        onReturnToLobby: () {
                          _recordMatch(gameState);
                          ref.read(gameStateProvider.notifier).reset();
                          context.go('/lobby');
                        },
                      ),
                    ),

                  // === Back button ===
                  Positioned(
                    top: 4,
                    left: 4,
                    child: IconButton(
                      icon: const Icon(Icons.arrow_back, color: Colors.white70, size: 20),
                      onPressed: () => _showExitConfirmation(context),
                      tooltip: 'العودة',
                    ),
                  ),

                  // === Settings button ===
                  Positioned(
                    top: 4,
                    right: 4,
                    child: IconButton(
                      icon: const Icon(Icons.settings, color: Colors.white70, size: 20),
                      onPressed: () => _showSettings(context),
                      tooltip: 'الإعدادات',
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  void _recordMatch(GameState gameState) {
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
