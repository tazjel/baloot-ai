// Baloot AI — Root application widget.
//
// Sets up MaterialApp with GoRouter, theming, and RTL support.
// Theme preference is persisted via SharedPreferences.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';

/// Key for persisting theme mode.
const _themeKey = 'baloot_theme_mode';

// Theme mode provider — loads from prefs, defaults to system
final themeModeProvider =
    StateNotifierProvider<ThemeModeNotifier, ThemeMode>((ref) {
  return ThemeModeNotifier();
});

/// Notifier that persists theme mode to SharedPreferences.
class ThemeModeNotifier extends StateNotifier<ThemeMode> {
  ThemeModeNotifier() : super(ThemeMode.system) {
    _load();
  }

  Future<void> _load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_themeKey);
      if (saved == 'light') {
        state = ThemeMode.light;
      } else if (saved == 'dark') {
        state = ThemeMode.dark;
      }
      // 'system' or null → keep default
    } catch (_) {}
  }

  Future<void> setTheme(ThemeMode mode) async {
    state = mode;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(
        _themeKey,
        mode == ThemeMode.light
            ? 'light'
            : mode == ThemeMode.dark
                ? 'dark'
                : 'system',
      );
    } catch (_) {}
  }

  void toggle() {
    if (state == ThemeMode.dark) {
      setTheme(ThemeMode.light);
    } else {
      setTheme(ThemeMode.dark);
    }
  }
}

class BalootApp extends ConsumerWidget {
  const BalootApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeModeProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: MaterialApp.router(
        title: 'بلوت AI',
        debugShowCheckedModeBanner: false,

        // Theme
        theme: AppTheme.light,
        darkTheme: AppTheme.dark,
        themeMode: themeMode,

        // Router
        routerConfig: appRouter,
      ),
    );
  }
}
