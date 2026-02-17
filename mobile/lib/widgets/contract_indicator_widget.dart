import 'package:flutter/material.dart';
import '../core/theme/colors.dart';
import '../models/enums.dart';
import 'suit_icon_widget.dart';

/// Displays the current contract (SUN/HOKUM) and trump suit if applicable.
class ContractIndicatorWidget extends StatelessWidget {
  final GameMode gameMode;
  final Suit? trumpSuit;

  const ContractIndicatorWidget({
    super.key,
    required this.gameMode,
    this.trumpSuit,
  });

  @override
  Widget build(BuildContext context) {
    final isSun = gameMode == GameMode.sun;
    final color = isSun ? AppColors.info : AppColors.error;
    final label = isSun ? 'صن' : 'حكم';
    final icon = isSun ? Icons.wb_sunny_rounded : Icons.gavel_rounded;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.darkSurface.withOpacity(0.8),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color, width: 1.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 16),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
          if (!isSun && trumpSuit != null) ...[
            const SizedBox(width: 8),
            Container(width: 1, height: 16, color: AppColors.textMuted),
            const SizedBox(width: 8),
            SuitIconWidget(suit: trumpSuit!, size: 18),
          ],
        ],
      ),
    );
  }
}
