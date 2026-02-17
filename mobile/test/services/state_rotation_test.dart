import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/services/state_rotation.dart';
import 'package:baloot_ai/models/enums.dart';
import 'package:baloot_ai/models/game_state.dart';
import 'package:baloot_ai/models/card_model.dart';
import 'package:baloot_ai/models/player.dart';
import 'package:baloot_ai/models/bid.dart';

/// Helper to create a minimal game state with 4 players at standard positions.
GameState _makeState({
  int turnIndex = 0,
  int dealerIndex = 3,
  List<TableCard>? tableCards,
  Bid? bid,
  Map<String, List>? declarations,
}) {
  final players = [
    Player(position: PlayerPosition.bottom, name: 'P0', index: 0),
    Player(position: PlayerPosition.right, name: 'P1', index: 1),
    Player(position: PlayerPosition.top, name: 'P2', index: 2),
    Player(position: PlayerPosition.left, name: 'P3', index: 3),
  ];

  return GameState(
    players: players,
    currentTurnIndex: turnIndex,
    phase: GamePhase.playing,
    tableCards: tableCards ?? [],
    bid: bid ?? Bid(type: null, suit: null, bidder: null, doubled: false),
    teamScores: TeamScores(us: 0, them: 0),
    floorCard: null,
    dealerIndex: dealerIndex,
    biddingRound: 1,
    declarations: {},
    doublingLevel: DoublingLevel.normal,
    isLocked: false,
    matchScores: TeamScores(us: 0, them: 0),
    roundHistory: [],
    deck: [],
    lastTrick: null,
  );
}

void main() {
  group('rotateGameState — Player Array Rotation', () {
    test('myIdx=0 → no rotation (identity)', () {
      final state = _makeState();
      final rotated = rotateGameState(state, 0);

      expect(rotated.players[0].name, 'P0');
      expect(rotated.players[1].name, 'P1');
      expect(rotated.players[2].name, 'P2');
      expect(rotated.players[3].name, 'P3');
    });

    test('myIdx=1 → P1 becomes index 0', () {
      final state = _makeState();
      final rotated = rotateGameState(state, 1);

      expect(rotated.players[0].name, 'P1');
      expect(rotated.players[1].name, 'P2');
      expect(rotated.players[2].name, 'P3');
      expect(rotated.players[3].name, 'P0');
    });

    test('myIdx=2 → P2 becomes index 0', () {
      final state = _makeState();
      final rotated = rotateGameState(state, 2);

      expect(rotated.players[0].name, 'P2');
      expect(rotated.players[1].name, 'P3');
      expect(rotated.players[2].name, 'P0');
      expect(rotated.players[3].name, 'P1');
    });

    test('myIdx=3 → P3 becomes index 0', () {
      final state = _makeState();
      final rotated = rotateGameState(state, 3);

      expect(rotated.players[0].name, 'P3');
      expect(rotated.players[1].name, 'P0');
      expect(rotated.players[2].name, 'P1');
      expect(rotated.players[3].name, 'P2');
    });
  });

  group('rotateGameState — Index Rotation', () {
    test('turnIndex rotates correctly', () {
      // Server turn=2, myIdx=1 → rotated=(2-1+4)%4=1
      final state = _makeState(turnIndex: 2);
      final rotated = rotateGameState(state, 1);
      expect(rotated.currentTurnIndex, 1);
    });

    test('dealerIndex rotates correctly', () {
      // Server dealer=3, myIdx=1 → rotated=(3-1+4)%4=2
      final state = _makeState(dealerIndex: 3);
      final rotated = rotateGameState(state, 1);
      expect(rotated.dealerIndex, 2);
    });

    test('turnIndex wraps around correctly', () {
      // Server turn=0, myIdx=3 → rotated=(0-3+4)%4=1
      final state = _makeState(turnIndex: 0);
      final rotated = rotateGameState(state, 3);
      expect(rotated.currentTurnIndex, 1);
    });

    test('identity rotation: myIdx=0 preserves indices', () {
      final state = _makeState(turnIndex: 2, dealerIndex: 1);
      final rotated = rotateGameState(state, 0);
      expect(rotated.currentTurnIndex, 2);
      expect(rotated.dealerIndex, 1);
    });
  });

  group('rotateGameState — Position Mapping', () {
    test('myIdx=0 → positions unchanged', () {
      final state = _makeState();
      final rotated = rotateGameState(state, 0);

      expect(rotated.players[0].position, PlayerPosition.bottom);
      expect(rotated.players[1].position, PlayerPosition.right);
      expect(rotated.players[2].position, PlayerPosition.top);
      expect(rotated.players[3].position, PlayerPosition.left);
    });

    test('myIdx=1 → Right becomes Bottom, etc.', () {
      final state = _makeState();
      final rotated = rotateGameState(state, 1);

      // P1 (was Right) → now Bottom (index 0)
      expect(rotated.players[0].position, PlayerPosition.bottom);
      // P2 (was Top) → now Right (index 1)
      expect(rotated.players[1].position, PlayerPosition.right);
      // P3 (was Left) → now Top (index 2)
      expect(rotated.players[2].position, PlayerPosition.top);
      // P0 (was Bottom) → now Left (index 3)
      expect(rotated.players[3].position, PlayerPosition.left);
    });

    test('myIdx=2 → Top becomes Bottom, etc.', () {
      final state = _makeState();
      final rotated = rotateGameState(state, 2);

      expect(rotated.players[0].position, PlayerPosition.bottom); // P2
      expect(rotated.players[1].position, PlayerPosition.right);  // P3
      expect(rotated.players[2].position, PlayerPosition.top);    // P0
      expect(rotated.players[3].position, PlayerPosition.left);   // P1
    });
  });

  group('rotateGameState — Table Cards', () {
    test('table card playedBy positions rotate', () {
      final tableCards = [
        TableCard(
          card: const CardModel(id: '1', suit: Suit.spades, rank: Rank.ace),
          playedBy: PlayerPosition.bottom,
        ),
        TableCard(
          card: const CardModel(id: '2', suit: Suit.hearts, rank: Rank.king),
          playedBy: PlayerPosition.right,
        ),
      ];
      final state = _makeState(tableCards: tableCards);
      final rotated = rotateGameState(state, 1);

      // Bottom → Left (when myIdx=1)
      expect(rotated.tableCards[0].playedBy, PlayerPosition.left);
      // Right → Bottom (when myIdx=1)
      expect(rotated.tableCards[1].playedBy, PlayerPosition.bottom);
    });
  });

  group('rotateGameState — Bid Rotation', () {
    test('bid bidder position rotates', () {
      final bid = Bid(
        type: GameMode.hokum,
        suit: Suit.hearts,
        bidder: PlayerPosition.right,
        doubled: false,
      );
      final state = _makeState(bid: bid);
      final rotated = rotateGameState(state, 1);

      // Right → Bottom (when myIdx=1)
      expect(rotated.bid.bidder, PlayerPosition.bottom);
      // Suit and type preserved
      expect(rotated.bid.suit, Suit.hearts);
      expect(rotated.bid.type, GameMode.hokum);
    });

    test('null bidder stays null', () {
      final bid = Bid(type: null, suit: null, bidder: null, doubled: false);
      final state = _makeState(bid: bid);
      final rotated = rotateGameState(state, 2);
      expect(rotated.bid.bidder, null);
    });
  });

  group('rotateGameState — Edge Cases', () {
    test('empty players → returns initial state', () {
      final emptyState = GameState(
        players: [],
        currentTurnIndex: 0,
        phase: GamePhase.waiting,
        tableCards: [],
        bid: Bid(type: null, suit: null, bidder: null, doubled: false),
        teamScores: TeamScores(us: 0, them: 0),
        floorCard: null,
        dealerIndex: 0,
        biddingRound: 1,
        declarations: {},
        doublingLevel: DoublingLevel.normal,
        isLocked: false,
        matchScores: TeamScores(us: 0, them: 0),
        roundHistory: [],
        deck: [],
        lastTrick: null,
      );
      final rotated = rotateGameState(emptyState, 2);
      expect(rotated.players, isEmpty);
    });

    test('myIdx out of range is clamped', () {
      final state = _makeState();
      // myIdx=10 should be clamped to 3
      final rotated = rotateGameState(state, 10);
      expect(rotated.players[0].name, 'P3'); // Same as myIdx=3
    });

    test('myIdx negative is clamped to 0', () {
      final state = _makeState();
      final rotated = rotateGameState(state, -1);
      expect(rotated.players[0].name, 'P0'); // Same as myIdx=0
    });
  });

  group('rotateGameState — Full Round Trip', () {
    test('rotating 4 times returns to original', () {
      final state = _makeState(turnIndex: 1, dealerIndex: 2);

      // Rotating by all 4 positions should cycle back
      var s = state;
      for (int i = 0; i < 4; i++) {
        s = rotateGameState(s, 1);
      }

      // After 4 single-step rotations, player names should cycle back
      // (positions will be re-mapped each time, but names preserve order)
      expect(s.players[0].name, state.players[0].name);
    });
  });
}
