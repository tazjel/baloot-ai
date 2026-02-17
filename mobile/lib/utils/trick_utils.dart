/// trickUtils.dart — Trick resolution and move validation.
///
/// Port of frontend/src/utils/trickUtils.ts
///
/// Core trick-play logic used by the game state manager:
/// - [getTrickWinner]: Determines which card wins a completed trick.
/// - [isValidMove]: Validates whether a card play is legal under Baloot rules.
/// - [getInvalidMoveReason]: Returns Arabic/English explanation for illegal plays
///   (used in Qayd dispute system).
import '../models/card_model.dart';
import '../models/enums.dart';
import 'scoring_utils.dart';

/// Determines the winner of a trick from [tableCards].
///
/// Returns the 0-based index of the winning card in the [tableCards] list.
/// Returns -1 if the list is empty.
///
/// Winner logic:
/// - Only cards matching the lead suit OR trump suit (in HOKUM) compete.
/// - Off-suit, non-trump cards have strength -1 (can never win).
/// - The card with the highest [getCardStrength] wins.
/// - In HOKUM, any trump card beats any non-trump card because trump
///   strength is offset by +100.
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

/// Validates whether playing [card] from [hand] is legal given [tableCards].
///
/// Baloot move validation rules:
/// 1. **Empty hand**: Always invalid.
/// 2. **Strict mode off**: Always valid (used in some tests).
/// 3. **Leading** (table empty): Any card is valid, EXCEPT in HOKUM when
///    the game is locked (doubled) — cannot lead trump if holding non-trump.
/// 4. **Following**: Must follow the lead suit if you have it in hand.
/// 5. **Void of lead suit in HOKUM**: Must play trump if you have any.
/// 6. **Void of both lead and trump**: Any card is valid (discard).
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

/// Returns a human-readable reason why playing [card] is invalid, or null
/// if the move is legal.
///
/// Used by the Qayd dispute system to explain violations to players.
/// Messages include Arabic terms (Renounce, Cut) matching the UI.
///
/// Checks the same rules as [isValidMove] but returns descriptive strings
/// instead of a boolean.
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
