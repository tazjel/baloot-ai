import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/services/leaderboard_service.dart';
import 'package:baloot_ai/widgets/tier_badge.dart';

void main() {
  group('LeaderboardEntry model', () {
    test('fromJson parses correctly', () {
      final json = {
        'rank': 1,
        'firstName': 'محمد',
        'lastName': 'العلي',
        'leaguePoints': 1850,
      };
      final entry = LeaderboardEntry.fromJson(json);
      expect(entry.rank, 1);
      expect(entry.firstName, 'محمد');
      expect(entry.lastName, 'العلي');
      expect(entry.leaguePoints, 1850);
    });
  });

  group('PlayerRating model', () {
    test('fromJson parses correctly', () {
      final json = {
        'email': 'test@example.com',
        'rating': 1200,
        'tier': 'Expert',
        'gamesPlayed': 25,
        'isPlacement': false,
        'placementGamesRemaining': 0,
      };
      final rating = PlayerRating.fromJson(json);
      expect(rating.email, 'test@example.com');
      expect(rating.rating, 1200);
      expect(rating.tier, 'Expert');
      expect(rating.gamesPlayed, 25);
      expect(rating.isPlacement, false);
      expect(rating.placementGamesRemaining, 0);
    });

    test('fromJson parses placement player', () {
      final json = {
        'email': 'new@example.com',
        'rating': 1000,
        'tier': 'Intermediate',
        'gamesPlayed': 3,
        'isPlacement': true,
        'placementGamesRemaining': 7,
      };
      final rating = PlayerRating.fromJson(json);
      expect(rating.isPlacement, true);
      expect(rating.placementGamesRemaining, 7);
    });
  });

  group('TierBadge widget', () {
    testWidgets('renders correct Arabic text for Grandmaster', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: TierBadge(tier: 'Grandmaster'))),
      );
      expect(find.text('أسطوري'), findsOneWidget);
    });

    testWidgets('renders correct Arabic text for Master', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: TierBadge(tier: 'Master'))),
      );
      expect(find.text('محترف'), findsOneWidget);
    });

    testWidgets('renders correct Arabic text for Expert', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: TierBadge(tier: 'Expert'))),
      );
      expect(find.text('خبير'), findsOneWidget);
    });

    testWidgets('renders correct Arabic text for Intermediate', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: TierBadge(tier: 'Intermediate'))),
      );
      expect(find.text('متوسط'), findsOneWidget);
    });

    testWidgets('renders correct Arabic text for Beginner', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: TierBadge(tier: 'Beginner'))),
      );
      expect(find.text('مبتدئ'), findsOneWidget);
    });

    testWidgets('uses gold color for Grandmaster', (tester) async {
      const badge = TierBadge(tier: 'Grandmaster');
      expect(badge.tierColor, const Color(0xFFFFD700));
    });

    testWidgets('uses grey color for Beginner', (tester) async {
      const badge = TierBadge(tier: 'Beginner');
      expect(badge.tierColor, const Color(0xFF9E9E9E));
    });

    testWidgets('uses bronze color for Expert', (tester) async {
      const badge = TierBadge(tier: 'Expert');
      expect(badge.tierColor, const Color(0xFFCD7F32));
    });
  });
}
