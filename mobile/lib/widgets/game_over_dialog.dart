/// game_over_dialog.dart — Match result overlay shown at game end.
///
/// Displays final scores, round history summary, and action buttons
/// (play again / return to lobby).
library;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme/colors.dart';
import '../models/game_state.dart';
import '../models/round_result.dart';
import 'confetti_overlay.dart';

/// Full-screen dialog shown when a match reaches 152 GP.
///
/// Shows the winning team, final scores, round-by-round breakdown,
/// and provides options to play again or return to lobby.
class GameOverDialog extends StatelessWidget {
  final TeamScores matchScores;
  final List<RoundResult> roundHistory;
  final VoidCallback onPlayAgain;
  final VoidCallback onReturnToLobby;

  const GameOverDialog({
    required this.matchScores,
    required this.roundHistory,
    required this.onPlayAgain,
    required this.onReturnToLobby,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final weWon = matchScores.us >= 152;
    final resultColor = weWon ? AppColors.success : AppColors.error;
    final resultText = weWon ? 'فوز!' : 'خسارة';
    final resultSubtext = weWon ? 'أحسنت! فزتم بالمباراة' : 'حظاً أوفر في المرة القادمة';

    // Haptic on show
    HapticFeedback.heavyImpact();

    return Stack(
      children: [
        Material(
      color: Colors.black.withOpacity(0.85),
      child: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Trophy / skull icon
                Icon(
                  weWon ? Icons.emoji_events_rounded : Icons.sentiment_dissatisfied_rounded,
                  size: 80,
                  color: resultColor,
                ),
                const SizedBox(height: 16),

                // Result text
                Text(
                  resultText,
                  style: TextStyle(
                    fontSize: 48,
                    fontWeight: FontWeight.bold,
                    color: resultColor,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  resultSubtext,
                  style: const TextStyle(
                    fontSize: 16,
                    color: AppColors.textMuted,
                  ),
                ),

                const SizedBox(height: 32),

                // Score card
                _buildScoreCard(),

                const SizedBox(height: 24),

                // Round history
                if (roundHistory.isNotEmpty) ...[
                  const Text(
                    'تفاصيل الجولات',
                    style: TextStyle(
                      color: AppColors.textGold,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  _buildRoundHistoryTable(),
                  const SizedBox(height: 24),
                ],

                // Action buttons
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: onPlayAgain,
                    icon: const Icon(Icons.replay_rounded),
                    label: const Text(
                      'لعب مرة أخرى',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.goldPrimary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: onReturnToLobby,
                    icon: const Icon(Icons.home_rounded),
                    label: const Text('العودة للقائمة', style: TextStyle(fontSize: 16)),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.textLight,
                      side: const BorderSide(color: AppColors.textMuted),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
        if (weWon) const ConfettiOverlay(),
      ],
    );
  }

  Widget _buildScoreCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.cardSurface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.goldPrimary.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          // Header row
          const Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              Text('نحن', style: TextStyle(color: AppColors.teamUs, fontSize: 18, fontWeight: FontWeight.bold)),
              Text('النتيجة', style: TextStyle(color: AppColors.textMuted, fontSize: 14)),
              Text('هم', style: TextStyle(color: AppColors.teamThem, fontSize: 18, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(color: AppColors.primaryWithOpacity),
          const SizedBox(height: 12),
          // Score row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              Text(
                '${matchScores.us}',
                style: TextStyle(
                  fontSize: 40,
                  fontWeight: FontWeight.bold,
                  color: matchScores.us >= 152 ? AppColors.goldPrimary : AppColors.textLight,
                ),
              ),
              const Icon(Icons.sports_score_rounded, color: AppColors.goldPrimary, size: 28),
              Text(
                '${matchScores.them}',
                style: TextStyle(
                  fontSize: 40,
                  fontWeight: FontWeight.bold,
                  color: matchScores.them >= 152 ? AppColors.goldPrimary : AppColors.textLight,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '${roundHistory.length} جولات',
            style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildRoundHistoryTable() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardSurface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.darkBorder),
      ),
      child: Column(
        children: [
          // Table header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: const BoxDecoration(
              color: AppColors.secondarySurface,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(12),
                topRight: Radius.circular(12),
              ),
            ),
            child: const Row(
              children: [
                SizedBox(width: 36, child: Text('#', style: TextStyle(color: AppColors.textMuted, fontSize: 12), textAlign: TextAlign.center)),
                SizedBox(width: 48, child: Text('النوع', style: TextStyle(color: AppColors.textMuted, fontSize: 12), textAlign: TextAlign.center)),
                Expanded(child: Text('نحن', style: TextStyle(color: AppColors.teamUs, fontSize: 12, fontWeight: FontWeight.bold), textAlign: TextAlign.center)),
                Expanded(child: Text('هم', style: TextStyle(color: AppColors.teamThem, fontSize: 12, fontWeight: FontWeight.bold), textAlign: TextAlign.center)),
              ],
            ),
          ),
          // Table rows
          ...roundHistory.asMap().entries.map((entry) {
            final i = entry.key;
            final round = entry.value;
            final isEven = i % 2 == 0;
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: isEven ? Colors.transparent : Colors.white.withOpacity(0.03),
              child: Row(
                children: [
                  SizedBox(
                    width: 36,
                    child: Text(
                      '${round.roundNumber ?? (i + 1)}',
                      style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  SizedBox(
                    width: 48,
                    child: Text(
                      _modeLabel(round.gameMode),
                      style: TextStyle(
                        color: round.gameMode == 'HOKUM' ? AppColors.warning : AppColors.info,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      '${round.us.gamePoints ?? round.us.result}',
                      style: TextStyle(
                        color: round.winner == 'us' ? AppColors.success : AppColors.textLight,
                        fontWeight: round.winner == 'us' ? FontWeight.bold : FontWeight.normal,
                        fontSize: 14,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      '${round.them.gamePoints ?? round.them.result}',
                      style: TextStyle(
                        color: round.winner == 'them' ? AppColors.success : AppColors.textLight,
                        fontWeight: round.winner == 'them' ? FontWeight.bold : FontWeight.normal,
                        fontSize: 14,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  String _modeLabel(String? mode) {
    switch (mode) {
      case 'SUN':
        return 'صن';
      case 'HOKUM':
        return 'حكم';
      default:
        return '—';
    }
  }
}
