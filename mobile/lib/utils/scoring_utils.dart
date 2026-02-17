/// scoringUtils.dart — Card point values, strength rankings, and score calculation.
///
/// Port of frontend/src/utils/scoringUtils.ts
import '../models/card_model.dart';
import '../models/enums.dart';
import '../core/constants.dart';

/// Get card strength for trick resolution.
/// Higher number = stronger card.
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

/// Calculate final score with multipliers and kaboot.
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

/// Get point value of a card in the given mode.
int getCardPointValue(CardModel card, GameMode mode) {
  final modeKey = mode == GameMode.sun ? 'SUN' : 'HOKUM';
  return pointValues[modeKey]?[card.rank] ?? 0;
}
