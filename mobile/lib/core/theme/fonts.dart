/// App typography using bundled Tajawal font.
///
/// Tajawal is bundled offline in assets/fonts/ for zero-latency rendering.
/// The google_fonts dependency is kept as a fallback but not actively used.
library;

import 'package:flutter/material.dart';

/// Centralized font configuration for Baloot AI.
class AppFonts {
  AppFonts._();

  /// Primary font family — bundled in assets/fonts/.
  static const String fontFamily = 'Tajawal';

  /// Arabic-optimized text theme with Tajawal.
  static TextTheme get arabicTextTheme => const TextTheme(
        displayLarge:
            TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.bold),
        displayMedium:
            TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.bold),
        displaySmall:
            TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.bold),
        headlineMedium:
            TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.bold),
        titleLarge:
            TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.bold),
        titleMedium:
            TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.w500),
        bodyLarge: TextStyle(fontFamily: fontFamily),
        bodyMedium: TextStyle(fontFamily: fontFamily),
        labelLarge:
            TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.bold),
      );
}
