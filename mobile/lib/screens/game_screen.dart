import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/theme/colors.dart';
import '../state/audio/audio_notifier.dart';
// settings_dialog.dart will be created in M-F4
import '../state/ui/replay_notifier.dart';
import '../widgets/toast_overlay.dart';
import '../widgets/replay_controls.dart';
import '../widgets/player_widget.dart';
import '../models/player.dart';
import '../models/enums.dart';

class GameScreen extends ConsumerWidget {
  const GameScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 1. Initialize Audio Notifier (Watches GameState internally)
    ref.watch(audioNotifierProvider);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(color: AppColors.tableGreen),
        child: SafeArea(
          child: Stack(
            children: [
              // Table felt gradient
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


              // Center placeholder (Game Board)
              Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.style_rounded, size: 64, color: AppColors.goldPrimary),
                    const SizedBox(height: 16),
                    Text(
                      'طاولة البلوت',
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: Colors.white),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Game Board — Coming in M-F4',
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.white70),
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton.icon(
                      icon: const Icon(Icons.settings),
                      label: const Text('Settings'),
                      onPressed: () {
                        // TODO: SettingsDialog will be created in M-F4
                      },
                    ),
                    const SizedBox(height: 24),
                    // Temporary Player Widgets for Testing
                    Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: [
                        PlayerWidget(player: Player(position: PlayerPosition.bottom, name: 'You', index: 0), index: 0),
                        PlayerWidget(player: Player(position: PlayerPosition.right, name: 'Bot 1', index: 1), index: 1),
                        PlayerWidget(player: Player(position: PlayerPosition.top, name: 'Partner', index: 2), index: 2),
                        PlayerWidget(player: Player(position: PlayerPosition.left, name: 'Bot 2', index: 3), index: 3),
                      ],
                    ),
                  ],
                ),
              ),

              // Back button
              Positioned(
                top: 8,
                left: 8,
                child: IconButton(
                  icon: const Icon(Icons.arrow_back, color: Colors.white),
                  onPressed: () => context.go('/lobby'),
                ),
              ),

              // Overlays
              const ToastOverlay(),
              const ReplayControls(),
            ],
          ),
        ),
      ),
    );
  }
}
