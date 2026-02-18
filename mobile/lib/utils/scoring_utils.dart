/// scoringUtils.dart — Card point values, strength rankings, and score calculation.
///
/// Port of frontend/src/utils/scoringUtils.ts
///
/// This module provides three core functions used throughout the game:
/// - [getCardStrength]: Numeric strength for trick winner comparison.
/// - [calculateFinalScore]: End-of-round GP (game point) calculation with
///   multipliers, kaboot, and project bonuses.
/// - [getCardPointValue]: Raw abnat (point value) of individual cards.
library;
import '../models/card_model.dart';
import '../models/enums.dart';
import '../core/constants.dart';

/// Returns the numeric strength of [card] for trick winner comparison.
///
/// In SUN mode, all cards use a single ranking: 7 < 8 < 9 < J < Q < K < 10 < A.
/// In HOKUM mode, trump-suit cards use a special ranking where J and 9 are
/// promoted (7 < 8 < Q < K < 10 < A < 9 < J), and non-trump cards use the
/// normal HOKUM ranking (7 < 8 < J < Q < K < 10 < A).
///
/// Trump cards receive a +100 offset so they always beat non-trump cards
/// regardless of rank.
///
/// Returns an integer where higher = stronger. Cards not in the lead suit
/// or trump suit should be compared separately by the caller.
int getCardStrength(CardModel card, GameMode mode, [Suit? trumpSuit]) {
  if (mode == GameMode.sun) {
    return strengthOrder['SUN']!.indexOf(card.rank);
  } else {
    if (trumpSuit != null && card.suit == trumpSuit) {
      return 100 + strengthOrder['HOKUM_TRUMP']!.indexOf(card.rank);
    }
    return strengthOrder['HOKUM_NORMAL']!.indexOf(card.rank);
  }
}

/// Calculates the final game points (GP) for a team at end of round.
///
/// Applies the full scoring pipeline:
/// 1. **Kaboot** (sweep): If one team wins all 8 tricks, the winner gets a
///    fixed bonus (44 GP in SUN, 25 + project GP in HOKUM); loser gets 0.
/// 2. **Standard**: Combines [rawCardPoints] and [projectPoints], converts
///    to GP using the mode-specific formula (SUN: ×2/10, HOKUM: /10).
/// 3. **Doubling**: Multiplies GP by [doublingLevel] if > 1
///    (DOUBLE=2, TRIPLE=3, QUADRUPLE=4, GAHWA=flat 152).
///
/// Note: Baloot GP (2 per declaration) is added separately after this
/// function, as baloot is immune to all multipliers.
int calculateFinalScore({
  required int rawCardPoints,
  required int projectPoints,
  required bool isKaboot,
  required GameMode mode,
  required int doublingLevel,
  required bool isWinner,
}) {
  // Kaboot logic
  if (isKaboot) {
    if (!isWinner) return 0;
    if (mode == GameMode.hokum) return 25 + (projectPoints ~/ 10);
    return 44;
  }

  // Standard logic
  final totalRaw = rawCardPoints + projectPoints;
  int gamePoints;

  if (mode == GameMode.sun) {
    gamePoints = ((totalRaw * 2) / 10).round();
  } else {
    gamePoints = (totalRaw / 10).round();
  }

  // Doubling
  if (doublingLevel > 1) {
    gamePoints *= doublingLevel;
  }

  return gamePoints;
}

/// Returns the raw point value (abnat) of [card] in the given [mode].
///
/// SUN point values: A=11, 10=10, K=4, Q=3, J=2, others=0. Total=130.
/// HOKUM point values: J=20, 9=14, A=11, 10=10, K=3, Q=2, others=0. Total=162.
///
/// Returns 0 for cards with no point value (7, 8, and mode-specific zeros).
int getCardPointValue(CardModel card, GameMode mode) {
  final modeKey = mode == GameMode.sun ? 'SUN' : 'HOKUM';
  return pointValues[modeKey]?[card.rank] ?? 0;
}
