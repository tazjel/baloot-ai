/// sortUtils.dart — Hand sorting logic.
///
/// Port of frontend/src/utils/sortUtils.ts
import '../models/card_model.dart';
import '../models/enums.dart';
import '../core/constants.dart';

/// Returns a numeric rank for sorting.
/// Higher number = higher priority.
int getSortRank(CardModel card, GameMode mode, [Suit? trumpSuit]) {
  if (mode == GameMode.sun) {
    return strengthOrder['SUN']!.indexOf(card.rank);
  } else {
    if (trumpSuit != null && card.suit == trumpSuit) {
      return strengthOrder['HOKUM_TRUMP']!.indexOf(card.rank);
    } else {
      return strengthOrder['HOKUM_NORMAL']!.indexOf(card.rank);
    }
  }
}

/// Sort hand by suit grouping with color alternation.
/// Order: Spades, Diamonds, Clubs, Hearts (alternating black/red).
/// Internal sort by natural sequence (A, K, Q, J, 10, 9, 8, 7).
List<CardModel> sortHand(List<CardModel> hand, GameMode mode, [Suit? trumpSuit]) {
  if (hand.isEmpty) return [];

  final spades = hand.where((c) => c.suit == Suit.spades).toList();
  final hearts = hand.where((c) => c.suit == Suit.hearts).toList();
  final clubs = hand.where((c) => c.suit == Suit.clubs).toList();
  final diamonds = hand.where((c) => c.suit == Suit.diamonds).toList();

  int sorter(CardModel a, CardModel b) {
    return sequenceOrder.indexOf(a.rank) - sequenceOrder.indexOf(b.rank);
  }

  spades.sort(sorter);
  hearts.sort(sorter);
  clubs.sort(sorter);
  diamonds.sort(sorter);

  return [...spades, ...diamonds, ...clubs, ...hearts];
}
