// Baloot AI — Root application widget.
//
// Sets up MaterialApp with GoRouter, theming, and RTL support.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';

// Theme mode provider
final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.system);

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
