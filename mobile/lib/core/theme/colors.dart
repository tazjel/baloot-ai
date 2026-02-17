/// Baloot AI — Color palette.
///
/// Premium gold + table green + dark mode colors.
import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // Primary Gold
  static const Color goldPrimary = Color(0xFFD4AF37);
  static const Color goldLight = Color(0xFFF4D03F);
  static const Color goldDark = Color(0xFFB8860B);
  static const Color goldMuted = Color(0xFFC9A84C);

  // Table Felt
  static const Color tableGreen = Color(0xFF1A472A);
  static const Color tableGreenLight = Color(0xFF2D5A3F);
  static const Color tableGreenDark = Color(0xFF0E2B18);

  // Card Colors
  static const Color cardRed = Color(0xFFDC2626);
  static const Color cardBlack = Color(0xFF1A1A1A);
  static const Color cardBack = Color(0xFF1E3A8A);

  // Suit Colors (4-color mode)
  static const Color suitSpades = Color(0xFF1A1A1A);
  static const Color suitHearts = Color(0xFFDC2626);
  static const Color suitDiamonds = Color(0xFF2563EB); // Blue in 4-color
  static const Color suitClubs = Color(0xFF16A34A); // Green in 4-color

  // Team Colors
  static const Color teamUs = Color(0xFF3B82F6);
  static const Color teamThem = Color(0xFFEF4444);

  // UI
  static const Color success = Color(0xFF22C55E);
  static const Color error = Color(0xFFEF4444);
  static const Color warning = Color(0xFFF59E0B);
  static const Color info = Color(0xFF3B82F6);

  // Dark Mode Surfaces
  static const Color darkBg = Color(0xFF0D0907);
  static const Color darkSurface = Color(0xFF1C1917);
  static const Color darkCard = Color(0xFF292524);
  static const Color darkBorder = Color(0xFF44403C);

  // Light Mode Surfaces
  static const Color lightBg = Color(0xFFFFFBEB);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightCard = Color(0xFFF5F5F4);
  static const Color lightBorder = Color(0xFFE7E5E4);

  // Text
  static const Color textDark = Color(0xFF1C1917);
  static const Color textLight = Color(0xFFFAFAF9);
  static const Color textMuted = Color(0xFF78716C);
}
