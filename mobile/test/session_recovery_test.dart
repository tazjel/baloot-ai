/// Tests for M-MP4: Session Recovery — persistence and notifier.
///
/// Verifies that active game sessions can be saved/loaded/cleared
/// via SharedPreferences, and that SocketState supports session data.
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:baloot_ai/services/settings_persistence.dart';
import 'package:baloot_ai/state/game_socket_notifier.dart';

void main() {
  group('Session Persistence', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('saveActiveSession stores roomId and seatIndex', () async {
      await SettingsPersistence.saveActiveSession(
        roomId: 'room-abc',
        seatIndex: 2,
      );

      final session = await SettingsPersistence.loadActiveSession();
      expect(session, isNotNull);
      expect(session!.roomId, 'room-abc');
      expect(session.seatIndex, 2);
    });

    test('loadActiveSession returns null when nothing saved', () async {
      final session = await SettingsPersistence.loadActiveSession();
      expect(session, isNull);
    });

    test('clearActiveSession removes saved session', () async {
      await SettingsPersistence.saveActiveSession(
        roomId: 'room-xyz',
        seatIndex: 0,
      );
      await SettingsPersistence.clearActiveSession();
      final session = await SettingsPersistence.loadActiveSession();
      expect(session, isNull);
    });

    test('saveActiveSession overwrites previous session', () async {
      await SettingsPersistence.saveActiveSession(
        roomId: 'room-old',
        seatIndex: 1,
      );
      await SettingsPersistence.saveActiveSession(
        roomId: 'room-new',
        seatIndex: 3,
      );
      final session = await SettingsPersistence.loadActiveSession();
      expect(session!.roomId, 'room-new');
      expect(session.seatIndex, 3);
    });

    test('session persistence does not affect other settings', () async {
      // Save some game stats first
      SharedPreferences.setMockInitialValues({
        'baloot_games_played': 10,
        'baloot_games_won': 5,
      });

      await SettingsPersistence.saveActiveSession(
        roomId: 'room-test',
        seatIndex: 0,
      );

      // Verify stats are untouched
      final stats = await SettingsPersistence.loadStats();
      expect(stats.played, 10);
      expect(stats.won, 5);

      // Verify session is saved
      final session = await SettingsPersistence.loadActiveSession();
      expect(session!.roomId, 'room-test');
    });
  });

  group('SocketState', () {
    test('default state has no roomId', () {
      const state = SocketState();
      expect(state.roomId, isNull);
      expect(state.myIndex, 0);
      expect(state.isSendingAction, false);
    });

    test('copyWith creates new instance with updated fields', () {
      const state = SocketState();
      final updated = state.copyWith(roomId: 'room-1', myIndex: 2);
      expect(updated.roomId, 'room-1');
      expect(updated.myIndex, 2);
      expect(updated.isSendingAction, false);
    });

    test('copyWith preserves existing fields', () {
      final state = const SocketState(roomId: 'room-a', myIndex: 1);
      final updated = state.copyWith(isSendingAction: true);
      expect(updated.roomId, 'room-a');
      expect(updated.myIndex, 1);
      expect(updated.isSendingAction, true);
    });
  });
}
