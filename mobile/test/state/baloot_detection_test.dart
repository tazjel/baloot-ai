import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baloot_ai/state/ui/baloot_detection_provider.dart';
import 'package:baloot_ai/state/providers.dart';
import 'package:baloot_ai/models/enums.dart';
import 'package:baloot_ai/models/card_model.dart';
import 'package:baloot_ai/models/bid.dart';

void main() {
  CardModel card(Rank rank, Suit suit) => CardModel(id: '${rank.symbol}${suit.symbol}', rank: rank, suit: suit);

  test('balootDetectionProvider - returns hasBaloot=false during waiting phase', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    // Initial state is waiting phase.
    final state = container.read(balootDetectionProvider);
    expect(state.hasBaloot, false);
    expect(state.trumpSuit, null);
  });

  test('balootDetectionProvider - returns hasBaloot=false in SUN mode', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    // Set state to SUN playing phase
    container.read(gameStateProvider.notifier).updateGameState((prev) {
      return prev.copyWith(
        phase: GamePhase.playing,
        bid: const Bid(type: GameMode.sun, suit: null, bidder: PlayerPosition.bottom),
        players: [
           prev.players[0].copyWith(hand: [card(Rank.king, Suit.hearts), card(Rank.queen, Suit.hearts)]), // Even with potential baloot cards
           ...prev.players.sublist(1),
        ],
      );
    });

    final state = container.read(balootDetectionProvider);
    expect(state.hasBaloot, false); // SUN mode ignores baloot
    expect(state.trumpSuit, null);
  });

  test('balootDetectionProvider - returns hasBaloot=true when HOKUM + K+Q of trump in hand', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    // Set state to HOKUM playing phase with Hearts as trump
    container.read(gameStateProvider.notifier).updateGameState((prev) {
      return prev.copyWith(
        phase: GamePhase.playing,
        bid: const Bid(type: GameMode.hokum, suit: Suit.hearts, bidder: PlayerPosition.bottom),
        players: [
           prev.players[0].copyWith(hand: [
             card(Rank.king, Suit.hearts), 
             card(Rank.queen, Suit.hearts),
             card(Rank.seven, Suit.spades),
           ]),
           ...prev.players.sublist(1),
        ],
      );
    });

    final state = container.read(balootDetectionProvider);
    expect(state.hasBaloot, true);
    expect(state.trumpSuit, Suit.hearts);
  });

  test('balootDetectionProvider - returns hasBaloot=false when only K of trump (no Q)', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    // Set state to HOKUM playing phase with Hearts as trump
    container.read(gameStateProvider.notifier).updateGameState((prev) {
      return prev.copyWith(
        phase: GamePhase.playing,
        bid: const Bid(type: GameMode.hokum, suit: Suit.hearts, bidder: PlayerPosition.bottom),
        players: [
           prev.players[0].copyWith(hand: [
             card(Rank.king, Suit.hearts), 
             card(Rank.seven, Suit.hearts), // No Queen
           ]),
           ...prev.players.sublist(1),
        ],
      );
    });

    final state = container.read(balootDetectionProvider);
    expect(state.hasBaloot, false);
    expect(state.trumpSuit, Suit.hearts);
  });

  test('balootDetectionProvider - trumpSuit is correctly populated from bid', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    // Set state to HOKUM playing phase with Spades as trump
    container.read(gameStateProvider.notifier).updateGameState((prev) {
      return prev.copyWith(
        phase: GamePhase.playing,
        bid: const Bid(type: GameMode.hokum, suit: Suit.spades, bidder: PlayerPosition.bottom),
      );
    });

    final state = container.read(balootDetectionProvider);
    expect(state.trumpSuit, Suit.spades);
  });
}
