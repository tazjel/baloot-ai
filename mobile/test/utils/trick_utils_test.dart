import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/models/card_model.dart';
import 'package:baloot_ai/models/enums.dart';
import 'package:baloot_ai/utils/trick_utils.dart';

void main() {
  group('getTrickWinner', () {
    test('highest card of lead suit wins in SUN', () {
      final tableCards = [
        TableCard(card: const CardModel(id: '1', suit: Suit.spades, rank: Rank.seven), playedBy: PlayerPosition.bottom),
        TableCard(card: const CardModel(id: '2', suit: Suit.spades, rank: Rank.ace), playedBy: PlayerPosition.right),
        TableCard(card: const CardModel(id: '3', suit: Suit.spades, rank: Rank.king), playedBy: PlayerPosition.top),
        TableCard(card: const CardModel(id: '4', suit: Suit.hearts, rank: Rank.ace), playedBy: PlayerPosition.left),
      ];
      expect(getTrickWinner(tableCards, GameMode.sun, null), 1); // Ace of Spades
    });

    test('trump beats lead suit in HOKUM', () {
      final tableCards = [
        TableCard(card: const CardModel(id: '1', suit: Suit.spades, rank: Rank.ace), playedBy: PlayerPosition.bottom),
        TableCard(card: const CardModel(id: '2', suit: Suit.hearts, rank: Rank.seven), playedBy: PlayerPosition.right),
      ];
      expect(getTrickWinner(tableCards, GameMode.hokum, Suit.hearts), 1); // Trump 7 beats non-trump Ace
    });

    test('Jack is highest trump in HOKUM', () {
      final tableCards = [
        TableCard(card: const CardModel(id: '1', suit: Suit.hearts, rank: Rank.ace), playedBy: PlayerPosition.bottom),
        TableCard(card: const CardModel(id: '2', suit: Suit.hearts, rank: Rank.jack), playedBy: PlayerPosition.right),
      ];
      expect(getTrickWinner(tableCards, GameMode.hokum, Suit.hearts), 1); // Jack beats Ace in trump
    });

    test('empty table returns -1', () {
      expect(getTrickWinner([], GameMode.sun, null), -1);
    });
  });

  group('isValidMove', () {
    test('leading player can play any card', () {
      const card = CardModel(id: '1', suit: Suit.spades, rank: Rank.ace);
      const hand = [card];
      expect(
        isValidMove(card: card, hand: hand, tableCards: [], mode: GameMode.sun),
        true,
      );
    });

    test('must follow lead suit if in hand', () {
      const playCard = CardModel(id: '2', suit: Suit.hearts, rank: Rank.ace);
      const hand = [
        CardModel(id: '1', suit: Suit.spades, rank: Rank.seven),
        playCard,
      ];
      final tableCards = [
        TableCard(card: const CardModel(id: '3', suit: Suit.spades, rank: Rank.ace), playedBy: PlayerPosition.bottom),
      ];
      expect(
        isValidMove(card: playCard, hand: hand, tableCards: tableCards, mode: GameMode.sun),
        false, // Must play spade
      );
    });

    test('strict mode off allows any card', () {
      const card = CardModel(id: '1', suit: Suit.hearts, rank: Rank.seven);
      final tableCards = [
        TableCard(card: const CardModel(id: '2', suit: Suit.spades, rank: Rank.ace), playedBy: PlayerPosition.bottom),
      ];
      expect(
        isValidMove(
          card: card,
          hand: [card, const CardModel(id: '3', suit: Suit.spades, rank: Rank.seven)],
          tableCards: tableCards,
          mode: GameMode.sun,
          strictMode: false,
        ),
        true,
      );
    });

    test('HOKUM must cut with trump when void of lead suit', () {
      const trumpCard = CardModel(id: '1', suit: Suit.hearts, rank: Rank.seven);
      const nonTrumpCard = CardModel(id: '2', suit: Suit.diamonds, rank: Rank.ace);
      final hand = [trumpCard, nonTrumpCard];
      final tableCards = [
        TableCard(card: const CardModel(id: '3', suit: Suit.spades, rank: Rank.ace), playedBy: PlayerPosition.bottom),
      ];
      // Playing non-trump when holding trump + void of lead = invalid
      expect(
        isValidMove(card: nonTrumpCard, hand: hand, tableCards: tableCards, mode: GameMode.hokum, trumpSuit: Suit.hearts),
        false,
      );
      // Playing trump = valid
      expect(
        isValidMove(card: trumpCard, hand: hand, tableCards: tableCards, mode: GameMode.hokum, trumpSuit: Suit.hearts),
        true,
      );
    });
  });
}
