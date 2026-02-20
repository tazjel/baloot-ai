/// tier_badge.dart — Colored tier badge widget.
///
/// Displays the player's rank tier (Grandmaster→Beginner) with
/// appropriate color and Arabic label.
library;

import 'package:flutter/material.dart';

/// Displays a colored tier badge (Grandmaster/Master/Expert/Intermediate/Beginner).
class TierBadge extends StatelessWidget {
  /// The English tier name from the server.
  final String tier;

  /// Font size for the label text.
  final double fontSize;

  const TierBadge({super.key, required this.tier, this.fontSize = 12});

  /// Map tier to its display color.
  Color get tierColor {
    switch (tier) {
      case 'Grandmaster':
        return const Color(0xFFFFD700); // gold
      case 'Master':
        return const Color(0xFFC0C0C0); // silver
      case 'Expert':
        return const Color(0xFFCD7F32); // bronze
      case 'Intermediate':
        return const Color(0xFF4CAF50); // green
      default:
        return const Color(0xFF9E9E9E); // grey
    }
  }

  /// Map tier to Arabic display text.
  String get tierArabic {
    switch (tier) {
      case 'Grandmaster':
        return 'أسطوري';
      case 'Master':
        return 'محترف';
      case 'Expert':
        return 'خبير';
      case 'Intermediate':
        return 'متوسط';
      default:
        return 'مبتدئ';
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = tierColor;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withAlpha(40),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withAlpha(120)),
      ),
      child: Text(
        tierArabic,
        style: TextStyle(
          color: color,
          fontSize: fontSize,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
