/// Baloot AI — Theme configuration.
///
/// Light + Dark themes with Tajawal Arabic font.
library;
import 'package:flutter/material.dart';
import 'colors.dart';

class AppTheme {
  AppTheme._();

  /// Light theme
  static ThemeData get light => ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        fontFamily: 'Tajawal',
        colorScheme: const ColorScheme.light(
          primary: AppColors.goldPrimary,
          onPrimary: Colors.white,
          secondary: AppColors.tableGreen,
          onSecondary: Colors.white,
          surface: AppColors.lightSurface,
          onSurface: AppColors.textDark,
          error: AppColors.error,
          onError: Colors.white,
        ),
        scaffoldBackgroundColor: AppColors.lightBg,
        cardColor: AppColors.lightCard,
        dividerColor: AppColors.lightBorder,
        appBarTheme: const AppBarTheme(
          backgroundColor: AppColors.goldPrimary,
          foregroundColor: Colors.white,
          elevation: 0,
          centerTitle: true,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.goldPrimary,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: AppColors.goldPrimary,
          ),
        ),
        iconTheme: const IconThemeData(
          color: AppColors.goldPrimary,
        ),
        dialogTheme: DialogThemeData(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
      );

  /// Dark theme
  static ThemeData get dark => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        fontFamily: 'Tajawal',
        colorScheme: const ColorScheme.dark(
          primary: AppColors.goldPrimary,
          onPrimary: Colors.black,
          secondary: AppColors.tableGreen,
          onSecondary: Colors.white,
          surface: AppColors.darkSurface,
          onSurface: AppColors.textLight,
          error: AppColors.error,
          onError: Colors.white,
        ),
        scaffoldBackgroundColor: AppColors.darkBg,
        cardColor: AppColors.darkCard,
        dividerColor: AppColors.darkBorder,
        appBarTheme: const AppBarTheme(
          backgroundColor: AppColors.darkSurface,
          foregroundColor: AppColors.goldPrimary,
          elevation: 0,
          centerTitle: true,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.goldPrimary,
            foregroundColor: Colors.black,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: AppColors.goldLight,
          ),
        ),
        iconTheme: const IconThemeData(
          color: AppColors.goldPrimary,
        ),
        dialogTheme: DialogThemeData(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
      );
}
