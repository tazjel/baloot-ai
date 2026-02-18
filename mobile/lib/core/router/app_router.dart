/// Baloot AI — Navigation router.
///
/// 7 routes: /, /lobby, /multiplayer, /game, /profile, /about
library;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../screens/about_screen.dart';
import '../../screens/lobby_screen.dart';
import '../../screens/multiplayer_screen.dart';
import '../../screens/game_screen.dart';
import '../../screens/profile_screen.dart';
import '../../screens/splash_screen.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      name: 'splash',
      builder: (context, state) => const SplashScreen(),
    ),
    GoRoute(
      path: '/lobby',
      name: 'lobby',
      builder: (context, state) => const LobbyScreen(),
    ),
    GoRoute(
      path: '/multiplayer',
      name: 'multiplayer',
      builder: (context, state) => const MultiplayerScreen(),
    ),
    GoRoute(
      path: '/game',
      name: 'game',
      builder: (context, state) => const GameScreen(),
    ),
    GoRoute(
      path: '/profile',
      name: 'profile',
      builder: (context, state) => const ProfileScreen(),
    ),
    GoRoute(
      path: '/about',
      name: 'about',
      builder: (context, state) => const AboutScreen(),
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
