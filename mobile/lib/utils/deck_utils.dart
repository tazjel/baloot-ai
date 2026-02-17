/// deckUtils.dart — Deck generation with Fisher-Yates shuffle.
///
/// Port of frontend/src/utils/deckUtils.ts
import 'dart:math';
import '../models/card_model.dart';
import '../models/enums.dart';

/// Generate a shuffled 32-card Baloot deck.
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
