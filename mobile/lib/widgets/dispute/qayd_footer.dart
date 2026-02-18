/// qayd_footer.dart — Footer bar with timer and reporter info.
///
/// Port of frontend/src/components/dispute/QaydFooter.tsx
///
/// Shows a back button, reporter badge, and circular countdown timer.
/// Hidden on the RESULT step.
import 'package:flutter/material.dart';

import '../../models/enums.dart';
import 'qayd_types.dart';

class QaydFooter extends StatelessWidget {
  final QaydStep step;
  final int timeLeft;
  final int timerDuration;
  final String reporterName;
  final VoidCallback onBack;

  const QaydFooter({
    super.key,
    required this.step,
    required this.timeLeft,
    required this.timerDuration,
    required this.reporterName,
    required this.onBack,
  });

  @override
  Widget build(BuildContext context) {
    if (step == QaydStep.result) return const SizedBox.shrink();

    final showBack = step == QaydStep.violationSelect ||
        step == QaydStep.selectCard1 ||
        step == QaydStep.selectCard2;

    final timerProgress =
        timerDuration > 0 ? timeLeft / timerDuration : 0.0;
    final isLow = timeLeft <= 10;
    final timerColor = isLow ? const Color(0xFFF44336) : const Color(0xFFFBBF24);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: const BoxDecoration(
        color: qaydBgDark,
        border: Border(top: BorderSide(color: qaydBorder)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Back button
          if (showBack)
            GestureDetector(
              onTap: onBack,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFF555555),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  '← رجوع',
                  style: TextStyle(color: Color(0xFFD1D5DB), fontSize: 13),
                ),
              ),
            )
          else
            const SizedBox.shrink(),

          // Reporter badge + timer
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Reporter badge
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFF333333),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      ':المقيد',
                      style: TextStyle(
                        color: Color(0xFF9CA3AF),
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(width: 6),
                    const Text('👑', style: TextStyle(fontSize: 10)),
                    const SizedBox(width: 4),
                    Text(
                      reporterName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(width: 12),

              // Timer circle
              SizedBox(
                width: 40,
                height: 40,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    // Background ring
                    SizedBox(
                      width: 40,
                      height: 40,
                      child: CircularProgressIndicator(
                        value: 1.0,
                        strokeWidth: 3,
                        color: const Color(0xFF333333),
                        backgroundColor: Colors.transparent,
                      ),
                    ),
                    // Progress ring
                    SizedBox(
                      width: 40,
                      height: 40,
                      child: CircularProgressIndicator(
                        value: timerProgress,
                        strokeWidth: 3,
                        color: timerColor,
                        backgroundColor: Colors.transparent,
                      ),
                    ),
                    // Time text
                    Text(
                      '$timeLeft',
                      style: TextStyle(
                        color: isLow ? const Color(0xFFF87171) : Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
