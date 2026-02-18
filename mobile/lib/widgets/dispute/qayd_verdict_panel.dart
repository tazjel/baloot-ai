/// qayd_verdict_panel.dart — Verdict display after Qayd adjudication.
///
/// Port of frontend/src/components/dispute/QaydVerdictPanel.tsx
///
/// Shows the verdict (correct/wrong), evidence cards, penalty, and reason.
import 'package:flutter/material.dart';

import '../../core/theme/colors.dart';
import '../card_widget.dart';
import 'qayd_types.dart';

class QaydVerdictPanel extends StatelessWidget {
  final VerdictData? verdictData;
  final CardSelection? crimeCard;
  final CardSelection? proofCard;

  const QaydVerdictPanel({
    super.key,
    required this.verdictData,
    required this.crimeCard,
    required this.proofCard,
  });

  @override
  Widget build(BuildContext context) {
    if (verdictData == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 40),
        child: Center(
          child: CircularProgressIndicator(color: AppColors.goldPrimary),
        ),
      );
    }

    final data = verdictData!;
    final bannerColor =
        data.isCorrect ? const Color(0xFF4CAF50) : const Color(0xFFF44336);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Verdict banner
          _buildBanner(data, bannerColor),

          const SizedBox(height: 24),

          // Evidence cards
          if (crimeCard != null) _buildEvidence(),

          // Reason
          if (data.reason.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              data.reason,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFF9CA3AF),
                fontSize: 13,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildBanner(VerdictData data, Color bannerColor) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
      decoration: BoxDecoration(
        color: bannerColor,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: bannerColor.withOpacity(0.4),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          // Icon
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.2),
              shape: BoxShape.circle,
            ),
            child: Icon(
              data.isCorrect ? Icons.check_circle : Icons.cancel,
              color: Colors.white,
              size: 32,
            ),
          ),
          const SizedBox(width: 16),
          // Text
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  data.message,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                if (data.penalty > 0)
                  Text(
                    data.isCorrect
                        ? 'خسارة ${data.penalty} نقطة'
                        : 'عقوبة القيد الخاطئ: ${data.penalty}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: 13,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEvidence() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Crime card
        _buildEvidenceCard(
          card: crimeCard!,
          ringColor: qaydCrimeColor,
          label: 'الجريمة',
          labelColor: qaydCrimeColor,
        ),

        if (proofCard != null) ...[
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Icon(
              Icons.chevron_right,
              color: Color(0xFF6B7280),
              size: 24,
            ),
          ),
          // Proof card
          _buildEvidenceCard(
            card: proofCard!,
            ringColor: qaydProofColor,
            label: 'الدليل',
            labelColor: qaydProofColor,
          ),
        ],
      ],
    );
  }

  Widget _buildEvidenceCard({
    required CardSelection card,
    required Color ringColor,
    required String label,
    required Color labelColor,
  }) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: ringColor, width: 3),
          ),
          child: CardWidget(card: card.card, width: 64),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          style: TextStyle(
            color: labelColor,
            fontSize: 11,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
