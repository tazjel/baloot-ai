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
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/colors.dart';
import '../models/enums.dart';
import '../state/audio/audio_notifier.dart';
import '../state/providers.dart';
import '../widgets/action_dock.dart';
import '../widgets/game_arena.dart';
import '../widgets/hand_fan_widget.dart';
import '../widgets/player_avatar_widget.dart';
import '../widgets/table_hud_widget.dart';
import '../widgets/toast_overlay.dart';

/// Main game board screen.
///
/// Uses a Stack architecture with positioned layers for each
/// game board element. All player positions are relative to
/// the screen (bottom = human, top = partner, left/right = opponents).
class GameScreen extends ConsumerWidget {
  const GameScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Initialize audio notifier (watches game state internally)
    ref.watch(audioNotifierProvider);

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
                  const ToastOverlay(),

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

  void _showSettings(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.darkSurface,
        title: const Text('الإعدادات', style: TextStyle(color: AppColors.textLight)),
        content: const Text('إعدادات اللعبة (قريباً)', style: TextStyle(color: AppColors.textMuted)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إغلاق', style: TextStyle(color: AppColors.goldPrimary)),
          ),
        ],
      ),
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
