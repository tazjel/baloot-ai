/// sortUtils.dart — Hand sorting logic for display order.
///
/// Port of frontend/src/utils/sortUtils.ts
///
/// Baloot hands are displayed grouped by suit with color alternation
/// (black-red-black-red: ♠♦♣♥) and sorted within each group by natural
/// sequence order (A high to 7 low).
library;
import '../models/card_model.dart';
import '../models/enums.dart';
import '../core/constants.dart';

/// Returns a numeric sort rank for [card] within its suit group.
///
/// Uses [strengthOrder] to get mode-appropriate ranking:
/// - SUN: 7(0) < 8(1) < 9(2) < J(3) < Q(4) < K(5) < 10(6) < A(7)
/// - HOKUM trump: 7(0) < 8(1) < Q(2) < K(3) < 10(4) < A(5) < 9(6) < J(7)
/// - HOKUM non-trump: 7(0) < 8(1) < J(2) < Q(3) < K(4) < 10(5) < A(6)
///
/// Higher number = higher priority in display.
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

/// Sorts a player's [hand] for display with suit grouping and color alternation.
///
/// Suit order: ♠(black) → ♦(red) → ♣(black) → ♥(red).
/// Within each suit: cards are sorted by [sequenceOrder] index
/// (7, 8, 9, 10, J, Q, K, A — natural card sequence).
///
/// This matches the Saudi Baloot convention where players alternate
/// black/red suit groups for easy visual scanning.
///
/// Returns a new sorted list; does not modify the input.
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
