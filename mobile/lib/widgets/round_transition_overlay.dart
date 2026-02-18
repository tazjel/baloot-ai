/// round_transition_overlay.dart — Brief overlay between rounds.
///
/// Shows a quick score summary when a round ends before the next begins.
/// Displays the round winner, game points earned, and running match score.
library;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/colors.dart';
import '../state/providers.dart';

/// Overlay that briefly appears between rounds.
///
/// Shows for ~1.5 seconds during `isRoundTransitioning: true`.
class RoundTransitionOverlay extends ConsumerWidget {
  const RoundTransitionOverlay({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appState = ref.watch(gameStateProvider);
    final gs = appState.gameState;

    // Only show during round transitions
    if (gs.isRoundTransitioning != true) return const SizedBox.shrink();
    if (gs.roundHistory.isEmpty) return const SizedBox.shrink();

    final lastRound = gs.roundHistory.last;
    final weWon = lastRound.winner == 'us';
    final resultColor = weWon ? AppColors.success : AppColors.error;
    final usGP = lastRound.us.gamePoints ?? lastRound.us.result;
    final themGP = lastRound.them.gamePoints ?? lastRound.them.result;
    final mode = lastRound.gameMode;

    return AnimatedOpacity(
      opacity: 1.0,
      duration: const Duration(milliseconds: 300),
      child: Center(
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 40),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(0.85),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: resultColor.withOpacity(0.5), width: 2),
            boxShadow: [
              BoxShadow(
                color: resultColor.withOpacity(0.2),
                blurRadius: 20,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Round number + mode
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'الجولة ${lastRound.roundNumber ?? gs.roundHistory.length}',
                    style: const TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 14,
                    ),
                  ),
                  if (mode != null) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: mode == 'HOKUM'
                            ? AppColors.warning.withOpacity(0.2)
                            : AppColors.info.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        mode == 'HOKUM' ? 'حكم' : 'صن',
                        style: TextStyle(
                          color: mode == 'HOKUM' ? AppColors.warning : AppColors.info,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 12),

              // Score row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _ScoreColumn(
                    label: 'نحن',
                    gp: usGP,
                    color: AppColors.teamUs,
                    isWinner: weWon,
                  ),
                  Text(
                    '—',
                    style: TextStyle(color: resultColor, fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                  _ScoreColumn(
                    label: 'هم',
                    gp: themGP,
                    color: AppColors.teamThem,
                    isWinner: !weWon,
                  ),
                ],
              ),

              const SizedBox(height: 12),

              // Running match score
              Text(
                'المجموع: ${gs.matchScores.us} - ${gs.matchScores.them}',
                style: const TextStyle(
                  color: AppColors.goldPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ScoreColumn extends StatelessWidget {
  final String label;
  final int gp;
  final Color color;
  final bool isWinner;

  const _ScoreColumn({
    required this.label,
    required this.gp,
    required this.color,
    required this.isWinner,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text(
          '+$gp',
          style: TextStyle(
            color: isWinner ? AppColors.goldPrimary : AppColors.textLight,
            fontSize: 28,
            fontWeight: FontWeight.bold,
          ),
        ),
        if (isWinner)
          const Icon(Icons.emoji_events_rounded, color: AppColors.goldPrimary, size: 16),
      ],
    );
  }
}
