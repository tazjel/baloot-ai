import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/services/settings_persistence.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('loadStats returns default values when nothing saved', () async {
    final stats = await SettingsPersistence.loadStats();
    expect(stats.played, 0);
    expect(stats.won, 0);
    expect(stats.streak, 0);
    expect(stats.bestStreak, 0);
  });

  test('recordMatchResult tracks stats correctly (played, won, streak)', () async {
    // 1. Record a win
    await SettingsPersistence.recordMatchResult(won: true);
    var stats = await SettingsPersistence.loadStats();
    expect(stats.played, 1);
    expect(stats.won, 1);
    expect(stats.streak, 1);
    expect(stats.bestStreak, 1);

    // 2. Record another win
    await SettingsPersistence.recordMatchResult(won: true);
    stats = await SettingsPersistence.loadStats();
    expect(stats.played, 2);
    expect(stats.won, 2);
    expect(stats.streak, 2);
    expect(stats.bestStreak, 2);

    // 3. Record a loss
    await SettingsPersistence.recordMatchResult(won: false);
    stats = await SettingsPersistence.loadStats();
    expect(stats.played, 3);
    expect(stats.won, 2); // Won count shouldn't increase
    expect(stats.streak, 0); // Streak reset
    expect(stats.bestStreak, 2); // Best streak preserved

    // 4. Record a win again
    await SettingsPersistence.recordMatchResult(won: true);
    stats = await SettingsPersistence.loadStats();
    expect(stats.played, 4);
    expect(stats.won, 3);
    expect(stats.streak, 1);
    expect(stats.bestStreak, 2); // Best streak still 2
  });

  test('Player Name persistence', () async {
    expect(await SettingsPersistence.loadPlayerName(), isNull);

    await SettingsPersistence.savePlayerName('Ahmed');
    expect(await SettingsPersistence.loadPlayerName(), 'Ahmed');
  });

  test('First launch tracking', () async {
    expect(await SettingsPersistence.isFirstLaunch(), isTrue);

    await SettingsPersistence.markFirstLaunchComplete();
    expect(await SettingsPersistence.isFirstLaunch(), isFalse);
  });

  test('resetStats clears all stats and history', () async {
    // Setup some data
    await SettingsPersistence.recordMatchResult(won: true);

    // Add match history
    await SettingsPersistence.addMatchToHistory(MatchSummary(
      date: DateTime.now(),
      usScore: 152,
      themScore: 100,
      won: true,
      rounds: 10,
      difficulty: 'HARD',
    ));

    // Verify data exists
    var stats = await SettingsPersistence.loadStats();
    expect(stats.played, 1);
    expect((await SettingsPersistence.loadMatchHistory()).length, 1);

    // Reset
    await SettingsPersistence.resetStats();

    // Verify cleared
    stats = await SettingsPersistence.loadStats();
    expect(stats.played, 0);
    expect(stats.won, 0);
    expect(stats.streak, 0);
    expect(stats.bestStreak, 0);

    expect((await SettingsPersistence.loadMatchHistory()).isEmpty, isTrue);
  });
}
