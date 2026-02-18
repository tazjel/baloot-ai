/// settings_persistence.dart — SharedPreferences persistence for game settings.
///
/// Saves and loads user preferences (difficulty, timer, strict mode, sound,
/// theme, etc.) so they persist across app restarts.
import 'dart:convert';
import 'dart:developer' as dev;

import 'package:shared_preferences/shared_preferences.dart';

import '../models/enums.dart';
import '../models/game_settings.dart';

/// Keys used in SharedPreferences.
abstract class _Keys {
  static const String settings = 'baloot_game_settings';
  static const String playerName = 'baloot_player_name';
  static const String gamesPlayed = 'baloot_games_played';
  static const String gamesWon = 'baloot_games_won';
}

/// Persistence layer for game settings and player stats.
///
/// Uses SharedPreferences to store settings as JSON. All methods are
/// static for easy access without dependency injection.
class SettingsPersistence {
  SettingsPersistence._();

  // =========================================================================
  // Game Settings
  // =========================================================================

  /// Load saved game settings, or return defaults if none saved.
  static Future<GameSettings> loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonStr = prefs.getString(_Keys.settings);
      if (jsonStr == null) return const GameSettings();

      final map = jsonDecode(jsonStr) as Map<String, dynamic>;
      return GameSettings.fromJson(map);
    } catch (e) {
      dev.log('Failed to load settings: $e', name: 'SETTINGS');
      return const GameSettings();
    }
  }

  /// Save game settings to persistent storage.
  static Future<void> saveSettings(GameSettings settings) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonStr = jsonEncode(settings.toJson());
      await prefs.setString(_Keys.settings, jsonStr);
      dev.log('Settings saved', name: 'SETTINGS');
    } catch (e) {
      dev.log('Failed to save settings: $e', name: 'SETTINGS');
    }
  }

  // =========================================================================
  // Player Name
  // =========================================================================

  /// Load saved player name, or null if none saved.
  static Future<String?> loadPlayerName() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(_Keys.playerName);
    } catch (e) {
      return null;
    }
  }

  /// Save the player name.
  static Future<void> savePlayerName(String name) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_Keys.playerName, name);
    } catch (e) {
      dev.log('Failed to save player name: $e', name: 'SETTINGS');
    }
  }

  // =========================================================================
  // Player Stats
  // =========================================================================

  /// Load games played and won counts.
  static Future<({int played, int won})> loadStats() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return (
        played: prefs.getInt(_Keys.gamesPlayed) ?? 0,
        won: prefs.getInt(_Keys.gamesWon) ?? 0,
      );
    } catch (e) {
      return (played: 0, won: 0);
    }
  }

  /// Increment game stats after a match.
  static Future<void> recordMatchResult({required bool won}) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final played = (prefs.getInt(_Keys.gamesPlayed) ?? 0) + 1;
      final wonCount = (prefs.getInt(_Keys.gamesWon) ?? 0) + (won ? 1 : 0);
      await prefs.setInt(_Keys.gamesPlayed, played);
      await prefs.setInt(_Keys.gamesWon, wonCount);
      dev.log('Stats: $played played, $wonCount won', name: 'SETTINGS');
    } catch (e) {
      dev.log('Failed to record match result: $e', name: 'SETTINGS');
    }
  }

  // =========================================================================
  // Convenience — Lobby Quick Settings
  // =========================================================================

  /// Save just the lobby-relevant settings (difficulty, timer, strict).
  static Future<void> saveLobbySettings({
    required BotDifficulty difficulty,
    required double timerDuration,
    required bool strictMode,
  }) async {
    final current = await loadSettings();
    await saveSettings(current.copyWith(
      botDifficulty: difficulty,
      turnDuration: timerDuration,
      strictMode: strictMode,
    ));
  }
}
