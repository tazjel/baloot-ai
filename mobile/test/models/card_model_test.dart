import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/models/card_model.dart';
import 'package:baloot_ai/models/enums.dart';

void main() {
  group('CardModel', () {
    test('fromJson and toJson round-trip', () {
      final json = {'id': 'c1', 'suit': '♠', 'rank': 'A', 'value': 7};
      final card = CardModel.fromJson(json);

      expect(card.suit, Suit.spades);
      expect(card.rank, Rank.ace);
      expect(card.id, 'c1');

      final output = card.toJson();
      expect(output['suit'], '♠');
      expect(output['rank'], 'A');
    });

    test('key returns rank+suit', () {
      const card = CardModel(id: 'c1', suit: Suit.hearts, rank: Rank.king);
      expect(card.key, 'K♥');
    });

    test('equality by suit and rank', () {
      const a = CardModel(id: '1', suit: Suit.spades, rank: Rank.ace);
      const b = CardModel(id: '2', suit: Suit.spades, rank: Rank.ace);
      expect(a, equals(b)); // Same suit+rank, different id
    });

    test('toString', () {
      const card = CardModel(id: 'c', suit: Suit.diamonds, rank: Rank.ten);
      expect(card.toString(), '10♦');
    });
  });

  group('TableCard', () {
    test('fromJson with card object', () {
      final json = {
        'card': {'id': 'c1', 'suit': '♣', 'rank': 'J'},
        'playedBy': 'Bottom',
        'metadata': {'akka': true},
      };
      final tc = TableCard.fromJson(json);
      expect(tc.card.suit, Suit.clubs);
      expect(tc.card.rank, Rank.jack);
      expect(tc.playedBy, PlayerPosition.bottom);
      expect(tc.isAkka, true);
    });
  });

  group('Suit', () {
    test('fromSymbol parses all suits', () {
      expect(Suit.fromSymbol('♠'), Suit.spades);
      expect(Suit.fromSymbol('♥'), Suit.hearts);
      expect(Suit.fromSymbol('♦'), Suit.diamonds);
      expect(Suit.fromSymbol('♣'), Suit.clubs);
    });

    test('isRed / isBlack', () {
      expect(Suit.hearts.isRed, true);
      expect(Suit.diamonds.isRed, true);
      expect(Suit.spades.isBlack, true);
      expect(Suit.clubs.isBlack, true);
    });
  });

  group('Rank', () {
    test('fromSymbol parses all ranks', () {
      expect(Rank.fromSymbol('7'), Rank.seven);
      expect(Rank.fromSymbol('A'), Rank.ace);
      expect(Rank.fromSymbol('10'), Rank.ten);
      expect(Rank.fromSymbol('J'), Rank.jack);
    });
  });

  group('GamePhase', () {
    test('fromValue parses phases', () {
      expect(GamePhase.fromValue('WAITING'), GamePhase.waiting);
      expect(GamePhase.fromValue('BIDDING'), GamePhase.bidding);
      expect(GamePhase.fromValue('PLAYING'), GamePhase.playing);
      expect(GamePhase.fromValue('GAMEOVER'), GamePhase.gameOver);
    });
  });

  group('LeagueTier', () {
    test('fromPoints assigns correct tier', () {
      expect(LeagueTier.fromPoints(0), LeagueTier.bronze);
      expect(LeagueTier.fromPoints(1200), LeagueTier.silver);
      expect(LeagueTier.fromPoints(1500), LeagueTier.gold);
      expect(LeagueTier.fromPoints(2000), LeagueTier.grandmaster);
    });
  });
}
