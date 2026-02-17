/// LobbyScreen — Game setup and settings.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/theme/colors.dart';

class LobbyScreen extends StatelessWidget {
  const LobbyScreen({super.key});

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
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'بلوت AI',
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        color: AppColors.goldPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Baloot AI',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: AppColors.textMuted,
                      ),
                ),
                const SizedBox(height: 48),
                ElevatedButton.icon(
                  onPressed: () => context.go('/game'),
                  icon: const Icon(Icons.play_arrow_rounded, size: 28),
                  label: const Text(
                    'ابدأ اللعبة',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                  ),
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: () => context.go('/multiplayer'),
                  icon: const Icon(Icons.people_rounded),
                  label: const Text('لعب جماعي'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.goldPrimary,
                    side: const BorderSide(color: AppColors.goldPrimary),
                    padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
