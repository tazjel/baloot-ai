/// table_hud_widget.dart — Scores, contract, and round info overlay.
///
/// Port of frontend/src/components/TableHUD.tsx
///
/// Displays game state information at the top of the game board:
/// - Match scores (Us vs Them)
/// - Current round scores
/// - Contract indicator (game mode + trump suit)
/// - Doubling level badge
/// - Round number
/// - Sawa state indicator
library;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/colors.dart';
import '../models/enums.dart';
import '../state/providers.dart';

/// Top-of-board HUD showing scores, contract, and round info.
class TableHudWidget extends ConsumerWidget {
  const TableHudWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appState = ref.watch(gameStateProvider);
    final gameState = appState.gameState;
    final phase = gameState.phase;

    // Only show during active play
    if (phase == GamePhase.waiting) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.5),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 0.5,
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              // Us score
              _ScorePill(
                label: 'نحن',
                matchScore: gameState.matchScores.us,
                roundScore: gameState.teamScores.us,
                color: AppColors.info,
              ),

              const Spacer(),

              // Contract indicator (center)
              _ContractBadge(
                gameMode: gameState.gameMode,
                trumpSuit: gameState.trumpSuit,
                doublingLevel: gameState.doublingLevel,
                roundNumber: gameState.roundHistory.length + 1,
                phase: phase,
              ),

              const Spacer(),

              // Them score
              _ScorePill(
                label: 'هم',
                matchScore: gameState.matchScores.them,
                roundScore: gameState.teamScores.them,
                color: AppColors.error,
                isRight: true,
              ),
            ],
          ),
          // Match progress bar
          if (gameState.matchScores.us > 0 || gameState.matchScores.them > 0)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: _MatchProgressBar(
                usScore: gameState.matchScores.us,
                themScore: gameState.matchScores.them,
              ),
            ),
        ],
      ),
    );
  }
}

// =============================================================================
// Score Pill
// =============================================================================

class _ScorePill extends StatelessWidget {
  final String label;
  final int matchScore;
  final int roundScore;
  final Color color;
  final bool isRight;

  const _ScorePill({
    required this.label,
    required this.matchScore,
    required this.roundScore,
    required this.color,
    this.isRight = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.3), width: 1),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 1),
          // Match score (large)
          Text(
            '$matchScore',
            style: TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          // Round score (small, below)
          if (roundScore > 0)
            Text(
              '($roundScore)',
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 10,
              ),
            ),
        ],
      ),
    );
  }
}

// =============================================================================
// Contract Badge
// =============================================================================

class _ContractBadge extends StatelessWidget {
  final GameMode? gameMode;
  final Suit? trumpSuit;
  final DoublingLevel doublingLevel;
  final int roundNumber;
  final GamePhase phase;

  const _ContractBadge({
    this.gameMode,
    this.trumpSuit,
    required this.doublingLevel,
    required this.roundNumber,
    required this.phase,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Round number
        Text(
          'الجولة $roundNumber',
          style: TextStyle(
            color: Colors.white.withOpacity(0.5),
            fontSize: 9,
          ),
        ),

        const SizedBox(height: 2),

        // Game mode + trump
        if (gameMode != null)
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                gameMode == GameMode.sun
                    ? Icons.wb_sunny_rounded
                    : Icons.gavel_rounded,
                color: gameMode == GameMode.sun
                    ? AppColors.info
                    : AppColors.error,
                size: 14,
              ),
              const SizedBox(width: 3),
              Text(
                gameMode == GameMode.sun ? 'صن' : 'حكم',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
              if (trumpSuit != null) ...[
                const SizedBox(width: 3),
                Text(
                  trumpSuit!.symbol,
                  style: TextStyle(
                    fontSize: 14,
                    color: trumpSuit!.isRed
                        ? AppColors.suitHearts
                        : AppColors.suitSpades,
                  ),
                ),
              ],
            ],
          )
        else if (phase == GamePhase.bidding)
          Text(
            'المزايدة',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 12,
            ),
          ),

        // Doubling badge
        if (doublingLevel != DoublingLevel.normal)
          Container(
            margin: const EdgeInsets.only(top: 2),
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
            decoration: BoxDecoration(
              color: AppColors.warning.withOpacity(0.3),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: AppColors.warning.withOpacity(0.6),
                width: 1,
              ),
            ),
            child: Text(
              _doublingText(doublingLevel),
              style: const TextStyle(
                color: AppColors.warning,
                fontSize: 9,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
      ],
    );
  }

  String _doublingText(DoublingLevel level) {
    switch (level) {
      case DoublingLevel.double_:
        return 'دبل';
      case DoublingLevel.triple:
        return 'تربل';
      case DoublingLevel.quadruple:
        return 'كبوت';
      case DoublingLevel.gahwa:
        return 'قهوة';
      default:
        return '';
    }
  }
}

// =============================================================================
// Match Progress Bar
// =============================================================================

class _MatchProgressBar extends StatelessWidget {
  final int usScore;
  final int themScore;

  const _MatchProgressBar({
    required this.usScore,
    required this.themScore,
  });

  @override
  Widget build(BuildContext context) {
    const target = 152.0;
    final usPct = (usScore / target).clamp(0.0, 1.0);
    final themPct = (themScore / target).clamp(0.0, 1.0);

    return SizedBox(
      height: 4,
      child: Row(
        children: [
          // Us progress (left → center)
          Expanded(
            child: Align(
              alignment: Alignment.centerRight,
              child: FractionallySizedBox(
                widthFactor: usPct,
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColors.info,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            ),
          ),
          // Center divider
          Container(
            width: 2,
            height: 4,
            color: Colors.white.withOpacity(0.3),
          ),
          // Them progress (right → center)
          Expanded(
            child: Align(
              alignment: Alignment.centerLeft,
              child: FractionallySizedBox(
                widthFactor: themPct,
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColors.error,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
