/// Baloot AI — Navigation router.
///
/// 4 routes: /lobby, /multiplayer, /game, /profile
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../screens/lobby_screen.dart';
import '../../screens/multiplayer_screen.dart';
import '../../screens/game_screen.dart';
import '../../screens/profile_screen.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/lobby',
  routes: [
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
