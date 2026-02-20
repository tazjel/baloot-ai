# M-MP8: Leaderboard + Ranking UI — Jules Task Spec

## Objective
Create a Flutter leaderboard screen and tier badge widgets for the Baloot AI multiplayer app. Players can view the top-ranked players and their own rank/tier.

## Existing Patterns (MUST follow)
- State management: Riverpod (see `mobile/lib/state/providers.dart`)
- Routing: GoRouter (see `mobile/lib/core/router/app_router.dart`)
- Theme: `AppColors` from `mobile/lib/core/theme/colors.dart`
- Arabic UI with RTL support
- Screen pattern: see `mobile/lib/screens/login_screen.dart` for structure

## Server Endpoints (already deployed)
- `GET /leaderboard` → `{"leaderboard": [{"rank": 1, "firstName": "...", "lastName": "...", "leaguePoints": 1500}, ...]}`
- `GET /elo/rating/<email>` → `{"email": "...", "rating": 1200, "tier": "Expert", "gamesPlayed": 25, "isPlacement": false, "placementGamesRemaining": 0}`

## Tier Definitions
```
Grandmaster: 1800+  → Color: #FFD700 (gold)
Master:      1500+  → Color: #C0C0C0 (silver)
Expert:      1200+  → Color: #CD7F32 (bronze)
Intermediate: 900+  → Color: #4CAF50 (green)
Beginner:      0+   → Color: #9E9E9E (grey)
```

## Deliverables

### 1. `mobile/lib/services/leaderboard_service.dart`
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

/// Service for fetching leaderboard and rating data from the server.
class LeaderboardService {
  final String baseUrl;
  LeaderboardService({this.baseUrl = 'http://10.0.2.2:3005'});

  /// Fetch top 50 leaderboard entries.
  Future<List<LeaderboardEntry>> fetchLeaderboard() async {
    final response = await http.get(Uri.parse('$baseUrl/leaderboard'));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return (data['leaderboard'] as List)
          .map((e) => LeaderboardEntry.fromJson(e))
          .toList();
    }
    throw Exception('Failed to fetch leaderboard: ${response.statusCode}');
  }

  /// Fetch a player's ELO rating and tier.
  Future<PlayerRating> fetchPlayerRating(String email) async {
    final response = await http.get(Uri.parse('$baseUrl/elo/rating/$email'));
    if (response.statusCode == 200) {
      return PlayerRating.fromJson(jsonDecode(response.body));
    }
    throw Exception('Failed to fetch rating: ${response.statusCode}');
  }
}

class LeaderboardEntry {
  final int rank;
  final String firstName;
  final String lastName;
  final int leaguePoints;

  LeaderboardEntry({
    required this.rank,
    required this.firstName,
    required this.lastName,
    required this.leaguePoints,
  });

  factory LeaderboardEntry.fromJson(Map<String, dynamic> json) {
    return LeaderboardEntry(
      rank: json['rank'] as int,
      firstName: json['firstName'] as String,
      lastName: json['lastName'] as String,
      leaguePoints: json['leaguePoints'] as int,
    );
  }
}

class PlayerRating {
  final String email;
  final int rating;
  final String tier;
  final int gamesPlayed;
  final bool isPlacement;
  final int placementGamesRemaining;

  PlayerRating({
    required this.email,
    required this.rating,
    required this.tier,
    required this.gamesPlayed,
    required this.isPlacement,
    required this.placementGamesRemaining,
  });

  factory PlayerRating.fromJson(Map<String, dynamic> json) {
    return PlayerRating(
      email: json['email'] as String,
      rating: json['rating'] as int,
      tier: json['tier'] as String,
      gamesPlayed: json['gamesPlayed'] as int,
      isPlacement: json['isPlacement'] as bool,
      placementGamesRemaining: json['placementGamesRemaining'] as int,
    );
  }
}
```

### 2. `mobile/lib/widgets/tier_badge.dart`
```dart
import 'package:flutter/material.dart';

/// Displays a colored tier badge (Grandmaster/Master/Expert/Intermediate/Beginner).
class TierBadge extends StatelessWidget {
  final String tier;
  final double fontSize;

  const TierBadge({super.key, required this.tier, this.fontSize = 12});

  Color get _tierColor {
    switch (tier) {
      case 'Grandmaster': return const Color(0xFFFFD700);
      case 'Master': return const Color(0xFFC0C0C0);
      case 'Expert': return const Color(0xFFCD7F32);
      case 'Intermediate': return const Color(0xFF4CAF50);
      default: return const Color(0xFF9E9E9E);
    }
  }

  String get _tierArabic {
    switch (tier) {
      case 'Grandmaster': return 'أسطوري';
      case 'Master': return 'محترف';
      case 'Expert': return 'خبير';
      case 'Intermediate': return 'متوسط';
      default: return 'مبتدئ';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _tierColor.withAlpha(40),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _tierColor.withAlpha(120)),
      ),
      child: Text(
        _tierArabic,
        style: TextStyle(
          color: _tierColor,
          fontSize: fontSize,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
```

### 3. `mobile/lib/screens/leaderboard_screen.dart`
A full-screen leaderboard with:
- AppBar with title "لوحة المتصدرين" (Leaderboard)
- Player's own rank card at the top (highlighted, with tier badge)
- Scrollable list of top 50 players with rank, name, league points, tier badge
- Top 3 have gold/silver/bronze medal icons
- Pull-to-refresh
- Loading spinner while fetching
- Error state with retry button
- Uses `AppColors.darkBg`, `AppColors.darkCard`, `AppColors.goldPrimary` for styling
- RTL text direction

### 4. `mobile/test/leaderboard_test.dart`
Write 8+ widget tests:
- `LeaderboardEntry.fromJson` parses correctly
- `PlayerRating.fromJson` parses correctly
- `TierBadge` renders correct Arabic text for each tier
- `TierBadge` uses correct color for Grandmaster (gold)
- `TierBadge` uses correct color for Beginner (grey)
- `LeaderboardScreen` shows loading indicator initially
- `LeaderboardScreen` shows player list after data loads (mock the service)
- `LeaderboardScreen` shows error state on failure

### 5. Register the route
Add to `mobile/lib/core/router/app_router.dart`:
```dart
GoRoute(
  path: '/leaderboard',
  builder: (context, state) => const LeaderboardScreen(),
),
```

## Rules
- DO NOT modify any existing files EXCEPT `app_router.dart` (add ONE route only)
- DO NOT modify theme files, providers, or game logic
- Follow the exact model classes shown above
- Use `AppColors` from `mobile/lib/core/theme/colors.dart` (import it)
- All user-visible text must be in Arabic
- Use `const` constructors wherever possible
- When done, **create a PR** with title: "[M-MP8] Leaderboard and ranking UI"
