/// LobbyScreen — Game setup with settings and start button.
///
/// Port of frontend/src/components/Lobby.tsx
///
/// Pre-game lobby where the player configures:
/// - Bot difficulty (Easy, Medium, Hard, Khalid)
/// - Timer duration (slider)
/// - Strict mode toggle
/// - Start game / Multiplayer buttons
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/colors.dart';
import '../models/enums.dart';
import '../state/providers.dart';

/// Pre-game lobby screen with settings and start button.
class LobbyScreen extends ConsumerStatefulWidget {
  const LobbyScreen({super.key});

  @override
  ConsumerState<LobbyScreen> createState() => _LobbyScreenState();
}

class _LobbyScreenState extends ConsumerState<LobbyScreen> {
  BotDifficulty _difficulty = BotDifficulty.hard;
  double _timerDuration = 15.0;
  bool _strictMode = true;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: isDark
                ? [AppColors.darkBg, AppColors.darkSurface]
                : [AppColors.lightBg, AppColors.lightSurface],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              children: [
                const SizedBox(height: 48),

                // === Title ===
                Text(
                  'بلوت AI',
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        color: AppColors.goldPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Baloot AI',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: AppColors.textMuted,
                      ),
                ),

                const SizedBox(height: 40),

                // === Settings Card ===
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.darkCard : AppColors.lightCard,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.05),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Section title
                      Row(
                        children: [
                          const Icon(Icons.tune_rounded, color: AppColors.goldPrimary, size: 20),
                          const SizedBox(width: 8),
                          Text(
                            'إعدادات اللعبة',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),

                      // Bot difficulty
                      Text(
                        'مستوى الصعوبة',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      const SizedBox(height: 8),
                      _DifficultySelector(
                        selected: _difficulty,
                        onChanged: (d) => setState(() => _difficulty = d),
                      ),

                      const SizedBox(height: 20),

                      // Timer duration slider
                      Row(
                        children: [
                          Text(
                            'وقت الدور',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                          ),
                          const Spacer(),
                          Text(
                            '${_timerDuration.round()} ثانية',
                            style: const TextStyle(
                              color: AppColors.goldPrimary,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      Slider(
                        value: _timerDuration,
                        min: 5,
                        max: 30,
                        divisions: 5,
                        activeColor: AppColors.goldPrimary,
                        onChanged: (v) => setState(() => _timerDuration = v),
                      ),

                      const SizedBox(height: 8),

                      // Strict mode toggle
                      SwitchListTile(
                        title: const Text('الوضع الصارم'),
                        subtitle: const Text('يمنع الحركات غير القانونية'),
                        value: _strictMode,
                        activeColor: AppColors.goldPrimary,
                        contentPadding: EdgeInsets.zero,
                        onChanged: (v) => setState(() => _strictMode = v),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 32),

                // === Start Game Button ===
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => _startGame(context),
                    icon: const Icon(Icons.play_arrow_rounded, size: 28),
                    label: const Text(
                      'ابدأ اللعبة',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.goldPrimary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                      elevation: 4,
                    ),
                  ),
                ),

                const SizedBox(height: 12),

                // === Multiplayer Button ===
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () => context.go('/multiplayer'),
                    icon: const Icon(Icons.people_rounded),
                    label: const Text('لعب جماعي'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.goldPrimary,
                      side: const BorderSide(color: AppColors.goldPrimary),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 48),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _startGame(BuildContext context) {
    // Apply settings
    ref.read(gameStateProvider.notifier).mergeSettings(
          botDifficulty: _difficulty,
          turnDuration: _timerDuration,
          strictMode: _strictMode,
        );

    // Navigate to game
    context.go('/game');

    // Start game via action dispatcher (create room + add bots)
    ref.read(actionDispatcherProvider.notifier).handlePlayerAction('START_GAME');
  }
}

// =============================================================================
// Difficulty Selector
// =============================================================================

class _DifficultySelector extends StatelessWidget {
  final BotDifficulty selected;
  final ValueChanged<BotDifficulty> onChanged;

  const _DifficultySelector({
    required this.selected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: BotDifficulty.values.map((d) {
        final isSelected = d == selected;
        return Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 3),
            child: GestureDetector(
              onTap: () => onChanged(d),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(
                  color: isSelected
                      ? _difficultyColor(d).withOpacity(0.2)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: isSelected
                        ? _difficultyColor(d)
                        : Colors.grey.withOpacity(0.3),
                    width: isSelected ? 2 : 1,
                  ),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      _difficultyIcon(d),
                      color: isSelected
                          ? _difficultyColor(d)
                          : AppColors.textMuted,
                      size: 20,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _difficultyLabel(d),
                      style: TextStyle(
                        color: isSelected
                            ? _difficultyColor(d)
                            : AppColors.textMuted,
                        fontSize: 11,
                        fontWeight:
                            isSelected ? FontWeight.bold : FontWeight.normal,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  String _difficultyLabel(BotDifficulty d) {
    switch (d) {
      case BotDifficulty.easy:
        return 'سهل';
      case BotDifficulty.medium:
        return 'متوسط';
      case BotDifficulty.hard:
        return 'صعب';
      case BotDifficulty.khalid:
        return 'خالد';
    }
  }

  IconData _difficultyIcon(BotDifficulty d) {
    switch (d) {
      case BotDifficulty.easy:
        return Icons.sentiment_satisfied_rounded;
      case BotDifficulty.medium:
        return Icons.psychology_rounded;
      case BotDifficulty.hard:
        return Icons.local_fire_department_rounded;
      case BotDifficulty.khalid:
        return Icons.auto_awesome;
    }
  }

  Color _difficultyColor(BotDifficulty d) {
    switch (d) {
      case BotDifficulty.easy:
        return AppColors.success;
      case BotDifficulty.medium:
        return AppColors.info;
      case BotDifficulty.hard:
        return AppColors.warning;
      case BotDifficulty.khalid:
        return AppColors.goldPrimary;
    }
  }
}
