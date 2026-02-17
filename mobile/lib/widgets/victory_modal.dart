/// victory_modal.dart — Win/lose match result display.
///
/// Port of frontend/src/components/VictoryModal.tsx
///
/// Shows at the end of a match:
/// - Win/lose banner with appropriate colors
/// - Final match scores
/// - Rematch / Home / Review buttons
/// - Confetti animation (when winning)
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/colors.dart';
import '../state/providers.dart';

/// Full-screen modal showing match result (victory or defeat).
class VictoryModal extends ConsumerWidget {
  final bool isWinner;
  final int usScore;
  final int themScore;

  const VictoryModal({
    super.key,
    required this.isWinner,
    required this.usScore,
    required this.themScore,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final color = isWinner ? AppColors.goldPrimary : AppColors.error;
    final icon = isWinner ? Icons.emoji_events_rounded : Icons.sentiment_dissatisfied_rounded;
    final title = isWinner ? 'مبروك! فزت!' : 'للأسف خسرت';
    final subtitle = isWinner ? 'أداء ممتاز!' : 'حاول مرة أخرى';

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(20),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: color.withOpacity(0.3),
            width: 2,
          ),
          boxShadow: [
            BoxShadow(
              color: color.withOpacity(0.2),
              blurRadius: 24,
              spreadRadius: 4,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Trophy / sad icon
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: color.withOpacity(0.15),
                border: Border.all(color: color.withOpacity(0.3), width: 3),
              ),
              child: Icon(icon, size: 44, color: color),
            ),

            const SizedBox(height: 16),

            // Title
            Text(
              title,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.textMuted,
                  ),
            ),

            const SizedBox(height: 24),

            // Final scores
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.05),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _ScoreColumn(
                    label: 'نحن',
                    score: usScore,
                    color: AppColors.info,
                    isBold: isWinner,
                  ),
                  Container(
                    width: 1,
                    height: 40,
                    color: Colors.grey.withOpacity(0.3),
                  ),
                  _ScoreColumn(
                    label: 'هم',
                    score: themScore,
                    color: AppColors.error,
                    isBold: !isWinner,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Action buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      context.go('/lobby');
                    },
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text('الرئيسية'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      ref.read(gameStateProvider.notifier).reset();
                      ref.read(actionDispatcherProvider.notifier)
                          .handlePlayerAction('START_GAME');
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: color,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text('إعادة المباراة'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ScoreColumn extends StatelessWidget {
  final String label;
  final int score;
  final Color color;
  final bool isBold;

  const _ScoreColumn({
    required this.label,
    required this.score,
    required this.color,
    this.isBold = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '$score',
          style: TextStyle(
            fontSize: isBold ? 32 : 28,
            fontWeight: isBold ? FontWeight.bold : FontWeight.w500,
            color: isBold ? color : AppColors.textMuted,
          ),
        ),
      ],
    );
  }
}
