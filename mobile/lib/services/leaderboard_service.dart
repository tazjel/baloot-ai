import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

/// Leaderboard entry model.
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

/// Player rating model.
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

/// Service to fetch leaderboard and player rating.
class LeaderboardService {
  static const String _baseUrl = 'http://10.0.2.2:3005';
  final http.Client _client;

  LeaderboardService({http.Client? client}) : _client = client ?? http.Client();

  /// Fetches the top 50 players.
  Future<List<LeaderboardEntry>> fetchLeaderboard() async {
    final response = await _client.get(Uri.parse('$_baseUrl/leaderboard'));

    if (response.statusCode == 200) {
      final data = json.decode(response.body) as Map<String, dynamic>;
      final List<dynamic> list = data['leaderboard'];
      return list.map((e) => LeaderboardEntry.fromJson(e)).toList();
    } else {
      throw Exception('Failed to load leaderboard');
    }
  }

  /// Fetches the rating for a specific player.
  Future<PlayerRating> fetchPlayerRating(String email) async {
    final response = await _client.get(Uri.parse('$_baseUrl/elo/rating/$email'));

    if (response.statusCode == 200) {
      return PlayerRating.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to load player rating');
    }
  }
}

/// Provider for LeaderboardService.
final leaderboardServiceProvider = Provider((ref) => LeaderboardService());
