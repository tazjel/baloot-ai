import 'package:flutter/material.dart';
import '../models/round_result.dart';
import '../core/theme/colors.dart';
import '../models/enums.dart';

/// Table displaying match history and scores.
class ScoreSheetWidget extends StatelessWidget {
  final List<RoundResult> roundHistory;

  const ScoreSheetWidget({super.key, required this.roundHistory});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.darkSurface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.goldMuted.withOpacity(0.3)),
      ),
      constraints: const BoxConstraints(maxHeight: 400),
      child: SingleChildScrollView(
        scrollDirection: Axis.vertical,
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            headingRowColor: WidgetStateProperty.all(AppColors.tableGreenDark),
            dataRowColor: WidgetStateProperty.all(AppColors.darkBg),
            columnSpacing: 24,
            columns: const [
              DataColumn(label: Text('الجولة', style: TextStyle(color: AppColors.goldLight, fontWeight: FontWeight.bold))),
              DataColumn(label: Text('لنا', style: TextStyle(color: AppColors.teamUs, fontWeight: FontWeight.bold))),
              DataColumn(label: Text('لهم', style: TextStyle(color: AppColors.teamThem, fontWeight: FontWeight.bold))),
              DataColumn(label: Text('النوع', style: TextStyle(color: AppColors.textMuted))),
              DataColumn(label: Text('الفائز', style: TextStyle(color: AppColors.goldLight))),
            ],
            rows: roundHistory.map((round) => _buildRow(round)).toList(),
          ),
        ),
      ),
    );
  }

  DataRow _buildRow(RoundResult round) {
    final usWon = round.winner == 'us';
    final themWon = round.winner == 'them';

    return DataRow(
      cells: [
        DataCell(Text(
          '#${round.roundNumber ?? '-'}',
          style: const TextStyle(color: AppColors.textLight),
        )),
        DataCell(Text(
          round.us.result.toString(),
          style: TextStyle(
            color: usWon ? AppColors.success : AppColors.textMuted,
            fontWeight: usWon ? FontWeight.bold : FontWeight.normal,
          ),
        )),
        DataCell(Text(
          round.them.result.toString(),
          style: TextStyle(
            color: themWon ? AppColors.success : AppColors.textMuted,
            fontWeight: themWon ? FontWeight.bold : FontWeight.normal,
          ),
        )),
        DataCell(_buildGameMode(round.gameMode)),
        DataCell(_buildWinnerIcon(round.winner)),
      ],
    );
  }

  Widget _buildGameMode(String? mode) {
    if (mode == null) return const Text('-');

    // Check if it matches 'SUN' or 'HOKUM' string, or map to enum if possible
    final isSun = mode == 'SUN' || mode == GameMode.sun.value;
    final label = isSun ? 'صن' : 'حكم';
    final color = isSun ? AppColors.info : AppColors.error;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12),
      ),
    );
  }

  Widget _buildWinnerIcon(String winner) {
    if (winner == 'us') {
      return const Icon(Icons.check_circle, color: AppColors.teamUs, size: 18);
    } else if (winner == 'them') {
      return const Icon(Icons.check_circle, color: AppColors.teamThem, size: 18);
    }
    return const SizedBox.shrink();
  }
}
