import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/models/card_model.dart';
import 'package:baloot_ai/models/enums.dart';
import 'package:baloot_ai/utils/akka_utils.dart';

void main() {
  CardModel card0(Rank rank, Suit suit) => CardModel(id: '${rank.symbol}${suit.symbol}', rank: rank, suit: suit);

  group('canDeclareAkka', () {
    test('returns false in SUN mode', () {
      final card = card0(Rank.king, Suit.spades);
      expect(
        canDeclareAkka(
          card: card,
          hand: [card],
          tableCards: [],
          mode: GameMode.sun,
          trumpSuit: null,
        ),
        false,
      );
    });

    test('returns false when table is not empty', () {
      final card = card0(Rank.king, Suit.spades);
      final tableCards = [
        TableCard(card: card0(Rank.seven, Suit.hearts), playedBy: PlayerPosition.right),
      ];
      expect(
        canDeclareAkka(
          card: card,
          hand: [card],
          tableCards: tableCards,
          mode: GameMode.hokum,
          trumpSuit: Suit.hearts,
        ),
        false,
      );
    });

    test('returns false for trump suit cards', () {
      final card = card0(Rank.king, Suit.hearts); // Hearts is trump
      expect(
        canDeclareAkka(
          card: card,
          hand: [card],
          tableCards: [],
          mode: GameMode.hokum,
          trumpSuit: Suit.hearts,
        ),
        false,
      );
    });

    test('returns false for Aces (self-evident boss)', () {
      final card = card0(Rank.ace, Suit.spades);
      expect(
        canDeclareAkka(
          card: card,
          hand: [card],
          tableCards: [],
          mode: GameMode.hokum,
          trumpSuit: Suit.hearts,
        ),
        false,
      );
    });

    test('returns true when card is highest remaining of its suit', () {
      // Ace is highest (out), 10 is next highest (held).
      // If Ace is played, 10 should be Akka eligible.
      final card = card0(Rank.ten, Suit.spades);
      final aceSpades = card0(Rank.ace, Suit.spades);
      
      final trick = {
        'cards': [aceSpades]
      };
      
      expect(
        canDeclareAkka(
          card: card,
          hand: [card],
          tableCards: [],
          mode: GameMode.hokum,
          trumpSuit: Suit.hearts,
          currentRoundTricks: [trick],
        ),
        true,
      );
    });

    test('returns false when higher card exists and not played', () {
      final card = card0(Rank.ten, Suit.spades); 
      // Ace is not played.
      expect(
        canDeclareAkka(
          card: card,
          hand: [card],
          tableCards: [],
          mode: GameMode.hokum,
          trumpSuit: Suit.hearts,
          currentRoundTricks: [],
        ),
        false,
      );
    });
  });

  group('canDeclareKawesh', () {
    test('returns true for hand with only 7s, 8s, 9s', () {
      final hand = [
        card0(Rank.seven, Suit.spades),
        card0(Rank.eight, Suit.hearts),
        card0(Rank.nine, Suit.diamonds),
        card0(Rank.seven, Suit.clubs),
        card0(Rank.eight, Suit.spades),
      ];
      expect(canDeclareKawesh(hand), true);
    });

    test('returns false when hand contains an Ace', () {
      final hand = [
        card0(Rank.ace, Suit.spades),
        card0(Rank.seven, Suit.hearts),
      ];
      expect(canDeclareKawesh(hand), false);
    });

    test('returns false when hand contains a 10', () {
      final hand = [
        card0(Rank.ten, Suit.spades),
        card0(Rank.seven, Suit.hearts),
      ];
      expect(canDeclareKawesh(hand), false);
    });

    test('returns false when hand contains a King', () {
      final hand = [
        card0(Rank.king, Suit.spades),
        card0(Rank.seven, Suit.hearts),
      ];
      expect(canDeclareKawesh(hand), false);
    });
  });

  group('hasBalootInHand', () {
    test('returns true when hand has K+Q of trump suit', () {
      final hand = [
        card0(Rank.king, Suit.hearts),
        card0(Rank.queen, Suit.hearts),
      ];
      expect(hasBalootInHand(hand, Suit.hearts), true);
    });

    test('returns false when missing Queen of trump', () {
      final hand = [
        card0(Rank.king, Suit.hearts),
        card0(Rank.seven, Suit.hearts),
      ];
      expect(hasBalootInHand(hand, Suit.hearts), false);
    });

    test('returns false when missing King of trump', () {
      final hand = [
        card0(Rank.queen, Suit.hearts),
        card0(Rank.seven, Suit.hearts),
      ];
      expect(hasBalootInHand(hand, Suit.hearts), false);
    });

    test('returns false when trumpSuit is null', () {
       final hand = [
        card0(Rank.king, Suit.hearts),
        card0(Rank.queen, Suit.hearts),
      ];
      expect(hasBalootInHand(hand, null), false);
    });
  });

  group('scanHandForAkka', () {
    test('returns false in SUN mode', () {
      expect(
        scanHandForAkka(
          hand: [],
          tableCards: [],
          mode: GameMode.sun,
          trumpSuit: null,
        ),
        false,
      );
    });

    test('returns false when table not empty', () {
      final tableCards = [
        TableCard(card: card0(Rank.seven, Suit.hearts), playedBy: PlayerPosition.right),
      ];
      expect(
        scanHandForAkka(
          hand: [],
          tableCards: tableCards,
          mode: GameMode.hokum,
          trumpSuit: Suit.hearts,
        ),
        false,
      );
    });

    test('returns true when hand contains eligible akka card', () {
       final card = card0(Rank.ten, Suit.spades);
       final aceSpades = card0(Rank.ace, Suit.spades);
       final trick = {'cards': [aceSpades]};
       
       expect(
        scanHandForAkka(
          hand: [card],
          tableCards: [],
          mode: GameMode.hokum,
          trumpSuit: Suit.hearts,
          currentRoundTricks: [trick],
        ),
        true,
      );
    });
  });
}
