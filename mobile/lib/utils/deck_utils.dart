/// deckUtils.dart — Deck generation with Fisher-Yates shuffle.
///
/// Port of frontend/src/utils/deckUtils.ts
///
/// Baloot uses a 32-card deck: 4 suits × 8 ranks (7, 8, 9, 10, J, Q, K, A).
/// This is the standard French-suited piquet deck used across all Saudi
/// Baloot variants.
import 'dart:math';
import '../models/card_model.dart';
import '../models/enums.dart';

/// Generates a new shuffled 32-card Baloot deck.
///
/// Creates one card for each combination of [Suit] × [Rank] (4×8 = 32),
/// assigns unique IDs in the format "♠-A-1", then shuffles using the
/// Fisher-Yates algorithm for uniform randomness.
///
/// Card values are set to 0 (point values are looked up dynamically
/// via [getCardPointValue] since they depend on game mode).
///
/// Returns a new shuffled list of [CardModel]s.
List<CardModel> generateDeck() {
  final deck = <CardModel>[];
  int idCounter = 1;

  for (final suit in Suit.values) {
    for (final rank in Rank.values) {
      deck.add(CardModel(
        id: '${suit.symbol}-${rank.symbol}-${idCounter++}',
        suit: suit,
        rank: rank,
        value: 0,
      ));
    }
  }

  // Fisher-Yates Shuffle
  final rng = Random();
  for (int i = deck.length - 1; i > 0; i--) {
    final j = rng.nextInt(i + 1);
    final temp = deck[i];
    deck[i] = deck[j];
    deck[j] = temp;
  }

  return deck;
}
