/// trickUtils.dart — Trick resolution and move validation.
///
/// Port of frontend/src/utils/trickUtils.ts
import '../models/card_model.dart';
import '../models/enums.dart';
import 'scoring_utils.dart';

/// Determine the winner of a trick.
/// Returns the index (0-3) of the winning card in [tableCards].
int getTrickWinner(
  List<TableCard> tableCards,
  GameMode mode,
  Suit? trumpSuit,
) {
  if (tableCards.isEmpty) return -1;

  final leadSuit = tableCards[0].card.suit;
  int highestStrength = -1;
  int winnerIndex = 0;

  for (int i = 0; i < tableCards.length; i++) {
    final card = tableCards[i].card;
    int strength;

    if (card.suit == leadSuit ||
        (mode == GameMode.hokum && card.suit == trumpSuit)) {
      strength = getCardStrength(card, mode, trumpSuit);
    } else {
      strength = -1;
    }

    if (strength > highestStrength) {
      highestStrength = strength;
      winnerIndex = i;
    }
  }

  return winnerIndex;
}

/// Check if a card is a valid move.
bool isValidMove({
  required CardModel card,
  required List<CardModel> hand,
  required List<TableCard> tableCards,
  required GameMode mode,
  Suit? trumpSuit,
  bool isLocked = false,
  bool strictMode = true,
}) {
  // Null safety
  if (hand.isEmpty) return false;
  if (!strictMode) return true;

  // Lead player
  if (tableCards.isEmpty) {
    if (isLocked && mode == GameMode.hokum && trumpSuit != null && card.suit == trumpSuit) {
      final hasNonTrump = hand.any((c) => c.suit != trumpSuit);
      if (hasNonTrump) return false;
    }
    return true;
  }

  final leadSuit = tableCards[0].card.suit;
  final hasLeadSuit = hand.any((c) => c.suit == leadSuit);

  // Rule 1: Must follow suit
  if (hasLeadSuit) {
    return card.suit == leadSuit;
  }

  // Rule 2: Must cut with trump in Hokum if possible
  if (mode == GameMode.hokum && trumpSuit != null) {
    final hasTrump = hand.any((c) => c.suit == trumpSuit);
    if (hasTrump && card.suit != trumpSuit) return false;
  }

  return true;
}

/// Explain why a move is invalid (for Qayd disputes).
String? getInvalidMoveReason({
  required CardModel card,
  required List<CardModel> hand,
  required List<TableCard> tableCards,
  required GameMode mode,
  Suit? trumpSuit,
  bool isLocked = false,
}) {
  if (tableCards.isEmpty) {
    if (isLocked && mode == GameMode.hokum && trumpSuit != null && card.suit == trumpSuit) {
      final hasNonTrump = hand.any((c) => c.suit != trumpSuit);
      if (hasNonTrump) {
        return 'You cannot help (lead trump) when the game is Locked (Doubled)!';
      }
    }
    return null;
  }

  final leadSuit = tableCards[0].card.suit;
  final hasLeadSuit = hand.any((c) => c.suit == leadSuit);

  if (hasLeadSuit) {
    if (card.suit != leadSuit) {
      return 'You have ${leadSuit.symbol} in your hand! You must follow suit (Renounce).';
    }
    return null;
  }

  if (mode == GameMode.hokum && trumpSuit != null) {
    final hasTrump = hand.any((c) => c.suit == trumpSuit);
    if (hasTrump && card.suit != trumpSuit) {
      return 'You have Trump (${trumpSuit.symbol})! You must Cut the trick since you cannot follow suit.';
    }
  }

  return null;
}
