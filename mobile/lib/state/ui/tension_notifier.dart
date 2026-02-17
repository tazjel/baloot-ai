/// tension_notifier.dart — Game tension level computation.
///
/// Port of frontend/src/hooks/useGameTension.ts (46 lines).
///
/// Computes a "heartbeat BPM" value based on current game state to
/// drive visual pulse effects. Higher tension = faster heartbeat.
///
/// ## Tension Factors
/// - Close score differential → higher tension
/// - Late in match (>100 GP) → higher tension
/// - Active trick (cards on table) → higher tension
/// - Bidding phase → lower base tension
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/enums.dart';
import '../../models/game_state.dart';

/// Tension level with computed BPM for heartbeat animation.
class TensionState {
  /// Heartbeat BPM (60–180). Higher = more tense.
  final double bpm;

  /// Normalized tension level (0.0–1.0).
  final double level;

  const TensionState({this.bpm = 60, this.level = 0.0});

  TensionState copyWith({double? bpm, double? level}) {
    return TensionState(
      bpm: bpm ?? this.bpm,
      level: level ?? this.level,
    );
  }
}

/// Computes game tension from match scores and game state.
///
/// Used by HeartbeatLayer for visual pulse overlay.
class TensionNotifier extends StateNotifier<TensionState> {
  TensionNotifier() : super(const TensionState());

  /// Recalculate tension from current game state.
  void updateFromGameState(GameState gameState) {
    if (gameState.phase == GamePhase.waiting ||
        gameState.phase == GamePhase.gameOver) {
      state = const TensionState();
      return;
    }

    double tension = 0.0;

    // Factor 1: Score closeness (0.0–0.4)
    final usScore = gameState.matchScores.us;
    final themScore = gameState.matchScores.them;
    final maxScore = usScore > themScore ? usScore : themScore;
    final diff = (usScore - themScore).abs();

    if (maxScore > 0) {
      final closeness = 1.0 - (diff / (maxScore + 1));
      tension += closeness * 0.4;
    }

    // Factor 2: Late in match (0.0–0.3)
    if (maxScore > 100) {
      tension += 0.3;
    } else if (maxScore > 60) {
      tension += 0.15;
    }

    // Factor 3: Cards on table (0.0–0.2)
    final tableCards = gameState.tableCards.length;
    tension += (tableCards / 4.0) * 0.2;

    // Factor 4: Playing phase boost (0.0–0.1)
    if (gameState.phase == GamePhase.playing) {
      tension += 0.1;
    }

    // Clamp to [0, 1]
    tension = tension.clamp(0.0, 1.0);

    // Convert to BPM (60–180)
    final bpm = 60.0 + (tension * 120.0);

    state = TensionState(bpm: bpm, level: tension);
  }
}

final tensionProvider =
    StateNotifierProvider<TensionNotifier, TensionState>((ref) {
  return TensionNotifier();
});
