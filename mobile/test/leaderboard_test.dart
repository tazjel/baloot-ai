import 'dart:async';
import 'package:baloot_ai/core/theme/colors.dart';
import 'package:baloot_ai/screens/leaderboard_screen.dart';
import 'package:baloot_ai/services/leaderboard_service.dart';
import 'package:baloot_ai/state/auth_notifier.dart';
import 'package:baloot_ai/state/providers.dart';
import 'package:baloot_ai/widgets/tier_badge.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockLeaderboardService extends Mock implements LeaderboardService {}

class MockAuthNotifier extends StateNotifier<AuthState> with Mock implements AuthNotifier {
  MockAuthNotifier(super.state);
}

void main() {
  group('Models', () {
    test('LeaderboardEntry.fromJson parses correctly', () {
      final json = {
        'rank': 1,
        'firstName': 'Ahmed',
        'lastName': 'Ali',
        'leaguePoints': 1500,
      };
      final entry = LeaderboardEntry.fromJson(json);
      expect(entry.rank, 1);
      expect(entry.firstName, 'Ahmed');
      expect(entry.lastName, 'Ali');
      expect(entry.leaguePoints, 1500);
    });

    test('PlayerRating.fromJson parses correctly', () {
      final json = {
        'email': 'test@test.com',
        'rating': 1200,
        'tier': 'Expert',
        'gamesPlayed': 25,
        'isPlacement': false,
        'placementGamesRemaining': 0,
      };
      final rating = PlayerRating.fromJson(json);
      expect(rating.email, 'test@test.com');
      expect(rating.rating, 1200);
      expect(rating.tier, 'Expert');
      expect(rating.gamesPlayed, 25);
      expect(rating.isPlacement, false);
      expect(rating.placementGamesRemaining, 0);
    });
  });

  group('TierBadge', () {
    testWidgets('TierBadge renders correct Arabic text for Grandmaster', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: TierBadge(tier: 'Grandmaster')),
      ));

      expect(find.text('أسطوري'), findsOneWidget);
    });

    testWidgets('TierBadge uses correct color for Grandmaster', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: TierBadge(tier: 'Grandmaster')),
      ));

      final container = tester.widget<Container>(find.byType(Container));
      final decoration = container.decoration as BoxDecoration;
      expect((decoration.border!.top.color), const Color(0xFFFFD700));
    });

    testWidgets('TierBadge uses correct color for Beginner', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: TierBadge(tier: 'Beginner')),
      ));

      final container = tester.widget<Container>(find.byType(Container));
      final decoration = container.decoration as BoxDecoration;
      expect((decoration.border!.top.color), const Color(0xFF9E9E9E));
    });
  });

  group('LeaderboardScreen', () {
    late MockLeaderboardService mockService;
    late MockAuthNotifier mockAuth;

    setUp(() {
      mockService = MockLeaderboardService();
      mockAuth = MockAuthNotifier(const AuthState(
        email: 'test@user.com',
        firstName: 'User',
        lastName: 'Test',
      ));
    });

    testWidgets('LeaderboardScreen shows loading indicator initially', (tester) async {
      final completer = Completer<List<LeaderboardEntry>>();

      when(() => mockService.fetchLeaderboard()).thenAnswer(
        (_) => completer.future,
      );
      when(() => mockService.fetchPlayerRating(any())).thenAnswer(
        (_) async => const PlayerRating(email: '', rating: 0, tier: 'Beginner', gamesPlayed: 0, isPlacement: false, placementGamesRemaining: 0),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            leaderboardServiceProvider.overrideWithValue(mockService),
            authProvider.overrideWith((ref) => mockAuth),
          ],
          child: const MaterialApp(home: LeaderboardScreen()),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      // Clean up by completing the future to avoid hanging tests or pending timer issues if any
      completer.complete([]);
      await tester.pump();
    });

    testWidgets('LeaderboardScreen shows player list after data loads', (tester) async {
      final entries = [
        const LeaderboardEntry(rank: 1, firstName: 'A', lastName: 'B', leaguePoints: 2000),
        const LeaderboardEntry(rank: 2, firstName: 'C', lastName: 'D', leaguePoints: 1000),
      ];
      final rating = const PlayerRating(
        email: 'test@user.com',
        rating: 1200,
        tier: 'Expert',
        gamesPlayed: 10,
        isPlacement: false,
        placementGamesRemaining: 0,
      );

      when(() => mockService.fetchLeaderboard()).thenAnswer((_) async => entries);
      when(() => mockService.fetchPlayerRating(any())).thenAnswer((_) async => rating);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            leaderboardServiceProvider.overrideWithValue(mockService),
            authProvider.overrideWith((ref) => mockAuth),
          ],
          child: const MaterialApp(home: LeaderboardScreen()),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('A B'), findsOneWidget);
      expect(find.text('C D'), findsOneWidget);
      expect(find.byIcon(Icons.emoji_events), findsWidgets); // Rank 1 medal
      expect(find.text('أنت'), findsOneWidget); // "You" text
    });

    testWidgets('LeaderboardScreen shows error state on failure', (tester) async {
      when(() => mockService.fetchLeaderboard()).thenThrow(Exception('Error'));
      when(() => mockService.fetchPlayerRating(any())).thenThrow(Exception('Error'));

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            leaderboardServiceProvider.overrideWithValue(mockService),
            authProvider.overrideWith((ref) => mockAuth),
          ],
          child: const MaterialApp(home: LeaderboardScreen()),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('تعذر تحميل البيانات. حاول مرة أخرى.'), findsOneWidget);
      expect(find.text('إعادة المحاولة'), findsOneWidget);
    });
  });
}
