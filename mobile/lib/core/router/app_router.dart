/// Baloot AI — Navigation router with custom page transitions.
///
/// 9 routes: /, /login, /signup, /lobby, /multiplayer, /game, /profile, /about
library;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../screens/about_screen.dart';
import '../../screens/lobby_screen.dart';
import '../../screens/login_screen.dart';
import '../../screens/multiplayer_screen.dart';
import '../../screens/game_screen.dart';
import '../../screens/leaderboard_screen.dart';
import '../../screens/profile_screen.dart';
import '../../screens/signup_screen.dart';
import '../../screens/splash_screen.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      name: 'splash',
      pageBuilder: (context, state) => CustomTransitionPage(
        key: state.pageKey,
        child: const SplashScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 300),
      ),
    ),
    GoRoute(
      path: '/leaderboard',
      builder: (context, state) => const LeaderboardScreen(),
    ),
    GoRoute(
      path: '/login',
      name: 'login',
      pageBuilder: (context, state) => CustomTransitionPage(
        key: state.pageKey,
        child: const LoginScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 400),
      ),
    ),
    GoRoute(
      path: '/signup',
      name: 'signup',
      pageBuilder: (context, state) => CustomTransitionPage(
        key: state.pageKey,
        child: const SignupScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 400),
      ),
    ),
    GoRoute(
      path: '/lobby',
      name: 'lobby',
      pageBuilder: (context, state) => CustomTransitionPage(
        key: state.pageKey,
        child: const LobbyScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 400),
      ),
    ),
    GoRoute(
      path: '/multiplayer',
      name: 'multiplayer',
      pageBuilder: (context, state) => CustomTransitionPage(
        key: state.pageKey,
        child: const MultiplayerScreen(),
        transitionsBuilder: _slideFromRight,
        transitionDuration: const Duration(milliseconds: 300),
      ),
    ),
    GoRoute(
      path: '/game',
      name: 'game',
      pageBuilder: (context, state) => CustomTransitionPage(
        key: state.pageKey,
        child: const GameScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          final scaleAnimation = Tween<double>(begin: 0.9, end: 1.0).animate(
            CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
          );
          return FadeTransition(
            opacity: animation,
            child: ScaleTransition(scale: scaleAnimation, child: child),
          );
        },
        transitionDuration: const Duration(milliseconds: 400),
      ),
    ),
    GoRoute(
      path: '/profile',
      name: 'profile',
      pageBuilder: (context, state) => CustomTransitionPage(
        key: state.pageKey,
        child: const ProfileScreen(),
        transitionsBuilder: _slideFromRight,
        transitionDuration: const Duration(milliseconds: 300),
      ),
    ),
    GoRoute(
      path: '/about',
      name: 'about',
      pageBuilder: (context, state) => CustomTransitionPage(
        key: state.pageKey,
        child: const AboutScreen(),
        transitionsBuilder: _slideFromBottom,
        transitionDuration: const Duration(milliseconds: 300),
      ),
    ),
  ],
  errorBuilder: (context, state) => Scaffold(
    body: Center(
      child: Text(
        'الصفحة غير موجودة\nPage not found',
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.headlineMedium,
      ),
    ),
  ),
);

/// Slide from right transition (for sub-screens).
Widget _slideFromRight(
  BuildContext context,
  Animation<double> animation,
  Animation<double> secondaryAnimation,
  Widget child,
) {
  final offsetAnimation = Tween<Offset>(
    begin: const Offset(1.0, 0.0),
    end: Offset.zero,
  ).animate(CurvedAnimation(parent: animation, curve: Curves.easeOutCubic));
  return SlideTransition(position: offsetAnimation, child: child);
}

/// Slide from bottom transition (for modal-like screens).
Widget _slideFromBottom(
  BuildContext context,
  Animation<double> animation,
  Animation<double> secondaryAnimation,
  Widget child,
) {
  final offsetAnimation = Tween<Offset>(
    begin: const Offset(0.0, 0.3),
    end: Offset.zero,
  ).animate(CurvedAnimation(parent: animation, curve: Curves.easeOutCubic));
  return FadeTransition(
    opacity: animation,
    child: SlideTransition(position: offsetAnimation, child: child),
  );
}
