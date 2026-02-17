import 'package:flutter/material.dart';
import '../core/theme/colors.dart';

/// Animated score counter with a semi-transparent background.
class ScoreBadgeWidget extends StatelessWidget {
  final int score;
  final Color color;
  final double fontSize;

  const ScoreBadgeWidget({
    super.key,
    required this.score,
    this.color = AppColors.textLight,
    this.fontSize = 24,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3), width: 1),
      ),
      child: TweenAnimationBuilder<int>(
        tween: IntTween(begin: 0, end: score),
        duration: const Duration(milliseconds: 800),
        curve: Curves.easeOutQuart,
        builder: (context, value, child) {
          return Text(
            value.toString(),
            style: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.bold,
              color: color,
              fontFamily: 'Roboto', // Or standard font
            ),
          );
        },
      ),
    );
  }
}
