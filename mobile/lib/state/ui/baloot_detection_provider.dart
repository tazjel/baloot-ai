/// baloot_detection_provider.dart — Auto-detect Baloot (K+Q of trump) in hand.
///
/// A computed provider that watches game state and returns whether the human
/// player currently holds both King and Queen of the trump suit.
///
/// Baloot detection only applies in HOKUM mode (SUN has no trump suit).
/// The UI layer (GameScreen) watches this provider and shows a toast
/// notification when baloot is first detected.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/enums.dart';
import '../../utils/akka_utils.dart';
import '../providers.dart';

/// State for baloot detection.
class BalootDetectionState {
  /// Whether the player currently holds K+Q of trump.
  final bool hasBaloot;

  /// The trump suit (null if SUN mode or no trump).
  final Suit? trumpSuit;

  const BalootDetectionState({
    this.hasBaloot = false,
    this.trumpSuit,
  });
}

/// Computed provider that checks if player 0 has Baloot (K+Q of trump).
///
/// Recomputes whenever gameStateProvider changes.
final balootDetectionProvider = Provider<BalootDetectionState>((ref) {
  final appState = ref.watch(gameStateProvider);
  final gs = appState.gameState;

  // Only check during HOKUM playing phase
  if (gs.phase != GamePhase.playing) {
    return const BalootDetectionState();
  }
  if (gs.bid.type != GameMode.hokum) {
    return const BalootDetectionState();
  }

  final trumpSuit = gs.bid.suit ?? gs.floorCard?.suit;
  if (trumpSuit == null) return const BalootDetectionState();
  if (gs.players.isEmpty) return const BalootDetectionState();

  final hand = gs.players[0].hand;
  final detected = hasBalootInHand(hand, trumpSuit);

  return BalootDetectionState(
    hasBaloot: detected,
    trumpSuit: trumpSuit,
  );
});
