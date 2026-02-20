import 'package:flutter/material.dart';

class TierBadge extends StatelessWidget {
  final String tier;
  final double fontSize;

  const TierBadge({
    super.key,
    required this.tier,
    this.fontSize = 12,
  });

  @override
  Widget build(BuildContext context) {
    final TierInfo info = _getTierInfo(tier);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: info.color.withOpacity(0.15),
        border: Border.all(color: info.color),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        info.arabicName,
        style: TextStyle(
          color: info.color,
          fontSize: fontSize,
          fontWeight: FontWeight.bold,
          fontFamily: 'Tajawal',
        ),
      ),
    );
  }

  TierInfo _getTierInfo(String tierName) {
    switch (tierName) {
      case 'Grandmaster':
        return const TierInfo(
          color: Color(0xFFFFD700), // Gold
          arabicName: 'أسطوري',
        );
      case 'Master':
        return const TierInfo(
          color: Color(0xFFC0C0C0), // Silver
          arabicName: 'محترف',
        );
      case 'Expert':
        return const TierInfo(
          color: Color(0xFFCD7F32), // Bronze
          arabicName: 'خبير',
        );
      case 'Intermediate':
        return const TierInfo(
          color: Color(0xFF4CAF50), // Green
          arabicName: 'متوسط',
        );
      case 'Beginner':
      default:
        return const TierInfo(
          color: Color(0xFF9E9E9E), // Grey
          arabicName: 'مبتدئ',
        );
    }
  }
}

class TierInfo {
  final Color color;
  final String arabicName;

  const TierInfo({required this.color, required this.arabicName});
}
