/// leaderboard_service.dart — HTTP client for leaderboard and ELO rating data.
///
/// Fetches top-50 leaderboard and per-player rating/tier from the server.
library;

import 'dart:convert';
import 'package:http/http.dart' as http;

/// A single entry on the leaderboard.
class LeaderboardEntry {
  final int rank;
  final String firstName;
  final String lastName;
  final int leaguePoints;

  const LeaderboardEntry({
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

/// A player's ELO rating with tier and placement info.
class PlayerRating {
  final String email;
  final int rating;
  final String tier;
  final int gamesPlayed;
  final bool isPlacement;
  final int placementGamesRemaining;

  const PlayerRating({
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

/// Service for fetching leaderboard and rating data from the server.
class LeaderboardService {
  final String baseUrl;
  final http.Client _client;

  LeaderboardService({
    this.baseUrl = 'http://10.0.2.2:3005',
    http.Client? client,
  }) : _client = client ?? http.Client();

  /// Fetch the top 50 leaderboard entries.
  Future<List<LeaderboardEntry>> fetchLeaderboard() async {
    final response = await _client.get(Uri.parse('$baseUrl/leaderboard'));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['leaderboard'] as List)
          .map((e) => LeaderboardEntry.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to fetch leaderboard: ${response.statusCode}');
  }

  /// Fetch a player's ELO rating and tier.
  Future<PlayerRating> fetchPlayerRating(String email) async {
    final response = await _client.get(Uri.parse('$baseUrl/elo/rating/$email'));
    if (response.statusCode == 200) {
      return PlayerRating.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>,
      );
    }
    throw Exception('Failed to fetch rating: ${response.statusCode}');
  }
}
