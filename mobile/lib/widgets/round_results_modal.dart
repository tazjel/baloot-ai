/// round_results_modal.dart — End-of-round scoring breakdown.
///
/// Port of frontend/src/components/RoundResultsModal.tsx
///
/// Shows detailed scoring after each round:
/// - Card points (abnat) for each team
/// - Project points (mashaari) for each team
/// - Game points awarded
/// - Khasara indicator
/// - Multiplier applied (doubling level)
/// - Baloot bonus
import 'package:flutter/material.dart';

import '../core/theme/colors.dart';
import '../models/round_result.dart';

/// Modal displaying detailed round scoring breakdown.
class RoundResultsModal extends StatelessWidget {
  final RoundResult result;

  const RoundResultsModal({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(20),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: AppColors.goldPrimary.withOpacity(0.2),
            width: 1,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Title
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.bar_chart_rounded, color: AppColors.goldPrimary, size: 24),
                const SizedBox(width: 8),
                Text(
                  'نتيجة الجولة',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),

            const SizedBox(height: 16),

            // Game mode badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(
                color: (result.gameMode == 'SUN' ? AppColors.info : AppColors.error)
                    .withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                result.gameMode == 'SUN' ? 'صن' : 'حكم',
                style: TextStyle(
                  color: result.gameMode == 'SUN' ? AppColors.info : AppColors.error,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Score table
            _ScoreTable(result: result),

            const SizedBox(height: 16),

            // Close button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.goldPrimary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text('متابعة'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ScoreTable extends StatelessWidget {
  final RoundResult result;

  const _ScoreTable({required this.result});

  @override
  Widget build(BuildContext context) {
    return Table(
      columnWidths: const {
        0: FlexColumnWidth(2),
        1: FlexColumnWidth(1),
        2: FlexColumnWidth(1),
      },
      children: [
        // Header
        _buildHeaderRow(),
        // Card points (abnat)
        _buildRow('الأبناط', '${result.us.abnat}', '${result.them.abnat}'),
        // Project points (mashaari)
        if (result.us.mashaari > 0 || result.them.mashaari > 0)
          _buildRow('المشاريع', '${result.us.mashaari}', '${result.them.mashaari}'),
        // Divider
        _buildDividerRow(),
        // Game points (bold)
        _buildRow('نقاط اللعبة', '${result.us.result}', '${result.them.result}',
            isBold: true),
      ],
    );
  }

  TableRow _buildHeaderRow() {
    return TableRow(
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Colors.grey.withOpacity(0.3)),
        ),
      ),
      children: [
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Text(''),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(
            'نحن',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppColors.info,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(
            'هم',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppColors.error,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
        ),
      ],
    );
  }

  TableRow _buildRow(String label, String us, String them, {bool isBold = false}) {
    final style = TextStyle(
      fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
      fontSize: isBold ? 16 : 14,
    );

    return TableRow(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Text(label, style: style),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Text(us, textAlign: TextAlign.center, style: style),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Text(them, textAlign: TextAlign.center, style: style),
        ),
      ],
    );
  }

  TableRow _buildDividerRow() {
    return TableRow(
      children: [
        Divider(color: Colors.grey.withOpacity(0.3)),
        Divider(color: Colors.grey.withOpacity(0.3)),
        Divider(color: Colors.grey.withOpacity(0.3)),
      ],
    );
  }
}
