/// state_rotation.dart — Server→client game state perspective rotation.
///
/// Port of frontend/src/hooks/useGameSocket.ts `rotateGameState()` (lines 66–161).
///
/// ## Why Rotation?
///
/// The server uses absolute seat indices (0–3) where index 0 is always the
/// first player who joined. But the client needs to display the game from
/// "my" perspective — the local player is always at position `Bottom` (index 0).
///
/// This module transforms server-absolute state into client-relative state:
/// - **Player array** is rotated so `myIdx` becomes index 0.
/// - **Integer indices** (currentTurnIndex, dealerIndex) use `(idx - myIdx + 4) % 4`.
/// - **Position strings** (Bottom/Right/Top/Left) are remapped so "my" server
///   position becomes Bottom.
/// - **All nested position references** (tableCards.playedBy, bid.bidder,
///   declarations keys/owners, lastTrick, akkaState.claimer) are also rotated.
///
/// ## Critical Invariant
///
/// `rotateGameState(serverState, myIdx).players[0]` is ALWAYS the local player.
///
/// This function is validated against 10 test vectors to ensure 100% parity
/// with the TypeScript implementation.
library;
import '../models/enums.dart';
import '../models/game_state.dart';
import '../models/card_model.dart';
import '../models/player.dart';
import '../models/bid.dart';
import '../models/declared_project.dart';

/// The four seat positions in clockwise order, matching the server protocol.
const _positionOrder = [
  PlayerPosition.bottom,
  PlayerPosition.right,
  PlayerPosition.top,
  PlayerPosition.left,
];

/// Server position string → enum mapping.
const _serverPosStrings = ['Bottom', 'Right', 'Top', 'Left'];

/// Rotates [serverState] from absolute server perspective to client-relative
/// perspective where [myIdx] becomes position 0 (Bottom).
///
/// Returns the rotated [GameState]. If the server state is invalid (no players),
/// returns [initialGameState].
///
/// The rotation formula for indices: `(serverIdx - myIdx + 4) % 4`
/// The rotation formula for arrays: `slice(myIdx) + slice(0, myIdx)`
GameState rotateGameState(GameState serverState, int myIdx) {
  try {
    if (serverState.players.isEmpty) {
      return initialGameState;
    }

    // Validate myIdx to safe range
    final safeMyIdx = myIdx.clamp(0, serverState.players.length - 1);

    // 1. Rotate Players Array
    final rotatedPlayers = [
      ...serverState.players.sublist(safeMyIdx),
      ...serverState.players.sublist(0, safeMyIdx),
    ];

    // 2. Rotate Turn and Dealer Indices
    final currentTurn = serverState.currentTurnIndex;
    final dealerIdx = serverState.dealerIndex;
    final rotatedTurnIndex = (currentTurn - safeMyIdx + 4) % 4;
    final rotatedDealerIndex = (dealerIdx - safeMyIdx + 4) % 4;

    // 3. Position Rotation Function
    PlayerPosition rotatePos(dynamic pos) {
      // Handle string positions from server
      int sIdx;
      if (pos is PlayerPosition) {
        sIdx = _positionOrder.indexOf(pos);
      } else if (pos is String) {
        sIdx = _serverPosStrings.indexOf(pos);
        if (sIdx == -1) {
          // Try matching enum values
          sIdx = _positionOrder.indexWhere((p) => p.value == pos);
        }
      } else {
        return PlayerPosition.bottom;
      }
      if (sIdx == -1) return PlayerPosition.bottom;
      final relativeIdx = (sIdx - myIdx + 4) % 4;
      return _positionOrder[relativeIdx];
    }

    // 4. Rotate All Position References

    // Players
    final newPlayers = rotatedPlayers.map((p) {
      return Player(
        position: rotatePos(p.position),
        name: p.name,
        avatar: p.avatar,
        hand: p.hand,
        score: p.score,
        isDealer: p.isDealer,
        isActive: p.isActive,
        actionText: p.actionText,
        lastReasoning: p.lastReasoning,
        index: p.index,
        isBot: p.isBot,
      );
    }).toList();

    // Table Cards
    final newTableCards = serverState.tableCards.map((tc) {
      return TableCard(
        card: tc.card,
        playedBy: rotatePos(tc.playedBy),
        metadata: tc.metadata,
      );
    }).toList();

    // Bid
    final newBid = Bid(
      type: serverState.bid.type,
      suit: serverState.bid.suit,
      bidder: serverState.bid.bidder != null
          ? rotatePos(serverState.bid.bidder!)
          : null,
      doubled: serverState.bid.doubled,
    );

    // Declarations (keyed by position)
    final newDeclarations = <String, List<DeclaredProject>>{};
    for (final entry in serverState.declarations.entries) {
      final newKey = rotatePos(entry.key).value;
      newDeclarations[newKey] = entry.value.map((d) {
        return DeclaredProject(
          type: d.type,
          rank: d.rank,
          suit: d.suit,
          owner: rotatePos(d.owner),
          score: d.score,
          cards: d.cards,
        );
      }).toList();
    }

    // Last Trick (stored as Map<String, dynamic>? in GameState)
    Map<String, dynamic>? newLastTrick;
    if (serverState.lastTrick != null) {
      final lt = Map<String, dynamic>.from(serverState.lastTrick!);
      // Rotate cards' playedBy positions
      if (lt['cards'] is List) {
        lt['cards'] = (lt['cards'] as List).map((c) {
          if (c is Map) {
            final card = Map<String, dynamic>.from(c);
            if (card.containsKey('playedBy')) {
              card['playedBy'] = rotatePos(card['playedBy']).value;
            }
            return card;
          }
          return c;
        }).toList();
      }
      // Rotate winner position
      if (lt.containsKey('winner') && lt['winner'] != null) {
        lt['winner'] = rotatePos(lt['winner']).value;
      }
      newLastTrick = lt;
    }

    // Akka State
    Map<String, dynamic>? newAkkaState;
    if (serverState.akkaState != null) {
      newAkkaState = Map<String, dynamic>.from(serverState.akkaState!);
      if (newAkkaState.containsKey('claimer')) {
        newAkkaState['claimer'] = rotatePos(newAkkaState['claimer']).value;
      }
    }

    return serverState.copyWith(
      players: newPlayers,
      currentTurnIndex: rotatedTurnIndex,
      dealerIndex: rotatedDealerIndex,
      tableCards: newTableCards,
      bid: newBid,
      declarations: newDeclarations,
      lastTrick: newLastTrick,
      akkaState: newAkkaState,
    );
  } catch (e) {
    // Critical error — return safe initial state
    return initialGameState;
  }
}

/// Default empty game state used when rotation fails or server state is invalid.
final initialGameState = GameState(
  players: [],
  currentTurnIndex: 0,
  phase: GamePhase.waiting,
  tableCards: [],
  bid: Bid(type: null, suit: null, bidder: null, doubled: false),
  teamScores: TeamScores(us: 0, them: 0),
  floorCard: null,
  dealerIndex: 3,
  biddingRound: 1,
  declarations: {},
  doublingLevel: DoublingLevel.normal,
  isLocked: false,
  matchScores: TeamScores(us: 0, them: 0),
  roundHistory: [],
  deck: [],
  lastTrick: null,
);
