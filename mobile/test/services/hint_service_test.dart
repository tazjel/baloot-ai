import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/models/models.dart';
import 'package:baloot_ai/services/hint_service.dart';

void main() {
  group('HintService', () {
    test('getHint returns null if no players', () {
      final state = GameState.initial();
      expect(HintService.getHint(state), isNull);
    });

    test('getBiddingHint suggests SUN for strong hand', () {
      final hand = [
        CardModel(id: '1', suit: Suit.hearts, rank: Rank.ace),
        CardModel(id: '2', suit: Suit.hearts, rank: Rank.ten),
        CardModel(id: '3', suit: Suit.diamonds, rank: Rank.ace),
        CardModel(id: '4', suit: Suit.diamonds, rank: Rank.ten),
        // 42 points so far > 26
      ];
      final state = GameState.initial().copyWith(
        phase: GamePhase.bidding,
        players: [
          Player(
            position: PlayerPosition.bottom,
            name: 'Me',
            hand: hand,
            index: 0,
          )
        ],
      );

      final hint = HintService.getBiddingHint(state, hand);
      expect(hint.action, 'SUN');
    });

    test('getPlayingHint suggests valid card', () {
      final hand = [
        CardModel(id: '1', suit: Suit.hearts, rank: Rank.seven),
        CardModel(id: '2', suit: Suit.hearts, rank: Rank.eight),
      ];
      final state = GameState.initial().copyWith(
        phase: GamePhase.playing,
        players: [
          Player(
            position: PlayerPosition.bottom,
            name: 'Me',
            hand: hand,
            index: 0,
          )
        ],
        bid: Bid(type: GameMode.sun, suit: null, bidder: PlayerPosition.bottom, doubled: false),
        tableCards: [],
      );

      final hint = HintService.getPlayingHint(state, hand, PlayerPosition.bottom);
      expect(hint.action, 'PLAY');
      expect(hint.cardIndex, isNotNull);
    });

    test('getPlayingHint follows suit', () {
       // Table has Hearts lead
       final hand = [
          CardModel(id: '1', suit: Suit.hearts, rank: Rank.nine), // Must play this
          CardModel(id: '2', suit: Suit.spades, rank: Rank.ace),
       ];
       final tableCards = [
          TableCard(card: CardModel(id: '3', suit: Suit.hearts, rank: Rank.seven), playedBy: PlayerPosition.right),
       ];

       final state = GameState.initial().copyWith(
        phase: GamePhase.playing,
        players: [
          Player(
            position: PlayerPosition.bottom,
            name: 'Me',
            hand: hand,
            index: 0,
          )
        ],
        bid: Bid(type: GameMode.sun, suit: null, bidder: PlayerPosition.right, doubled: false),
        tableCards: tableCards,
      );

      final hint = HintService.getPlayingHint(state, hand, PlayerPosition.bottom);
      expect(hint.action, 'PLAY');
      expect(hint.cardIndex, 0); // Should be index of Hearts 9
      expect(hint.reasoning, contains('9♥'));
    });

    test('getPlayingHint suggests Trump lead in Hokum', () {
        final hand = [
            CardModel(id: '1', suit: Suit.spades, rank: Rank.ace), // Trump
            CardModel(id: '2', suit: Suit.hearts, rank: Rank.ace),
        ];

        final state = GameState.initial().copyWith(
            phase: GamePhase.playing,
            players: [
              Player(
                position: PlayerPosition.bottom,
                name: 'Me',
                hand: hand,
                index: 0,
              )
            ],
            bid: Bid(type: GameMode.hokum, suit: Suit.spades, bidder: PlayerPosition.bottom, doubled: false),
            tableCards: [],
        );

        final hint = HintService.getPlayingHint(state, hand, PlayerPosition.bottom);
        expect(hint.action, 'PLAY');
        expect(hint.cardIndex, 0); // Should be Spades Ace (Trump)
        expect(hint.reasoning, contains('الحكم'));
    });
  });
}
