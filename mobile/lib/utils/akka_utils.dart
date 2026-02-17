/// akkaUtils.dart — Akka (Boss Card) declaration and Kawesh logic.
///
/// Port of frontend/src/utils/akkaUtils.ts
import '../models/card_model.dart';
import '../models/enums.dart';
import '../core/constants.dart';

/// Consistent card key (e.g., "A♠").
String cardKey(dynamic card) {
  if (card == null) return '';
  if (card is CardModel) return '${card.rank.symbol}${card.suit.symbol}';
  if (card is Map) {
    if (card.containsKey('card')) return cardKey(card['card']);
    final rank = card['rank'] as String?;
    final suit = card['suit'] as String?;
    if (rank != null && suit != null) return '$rank$suit';
  }
  return '';
}

/// Build a set of all played card keys.
Set<String> buildPlayedCardsSet([
  List<dynamic> currentRoundTricks = const [],
  List<dynamic> tableCards = const [],
]) {
  final played = <String>{};

  for (final trick in currentRoundTricks) {
    final cards = (trick is Map ? trick['cards'] : null) as List? ?? [];
    for (final c in cards) {
      final key = cardKey(c);
      if (key.isNotEmpty) played.add(key);
    }
  }

  for (final tc in tableCards) {
    final key = cardKey(tc is Map ? (tc['card'] ?? tc) : tc);
    if (key.isNotEmpty) played.add(key);
  }

  return played;
}

/// Check if a card qualifies for Akka declaration.
///
/// Rules:
///   1. HOKUM only
///   2. Table must be empty (leading)
///   3. Card suit must NOT be trump
///   4. Card rank must NOT be Ace
///   5. Card must be the highest remaining card of its suit
bool canDeclareAkka({
  required CardModel card,
  required List<CardModel> hand,
  required List<TableCard> tableCards,
  required GameMode mode,
  Suit? trumpSuit,
  List<dynamic> currentRoundTricks = const [],
}) {
  if (mode != GameMode.hokum) return false;
  if (tableCards.isNotEmpty) return false;
  if (trumpSuit != null && card.suit == trumpSuit) return false;
  if (card.rank == Rank.ace) return false;

  final playedCards = buildPlayedCardsSet(currentRoundTricks, []);
  final order = strengthOrder['HOKUM_NORMAL']!;
  final myRankIdx = order.indexOf(card.rank);
  if (myRankIdx == -1) return false;

  for (int i = myRankIdx + 1; i < order.length; i++) {
    final higherRank = order[i];
    final sig = '${higherRank.symbol}${card.suit.symbol}';

    if (playedCards.contains(sig)) continue;

    final weHoldIt = hand.any((c) => c.rank == higherRank && c.suit == card.suit);
    if (weHoldIt) return false;

    return false;
  }

  return true;
}

/// Check if ANY card in hand is eligible for Akka.
bool scanHandForAkka({
  required List<CardModel> hand,
  required List<TableCard> tableCards,
  required GameMode mode,
  Suit? trumpSuit,
  List<dynamic> currentRoundTricks = const [],
}) {
  if (mode != GameMode.hokum) return false;
  if (tableCards.isNotEmpty) return false;

  for (final card in hand) {
    if (canDeclareAkka(
      card: card,
      hand: hand,
      tableCards: tableCards,
      mode: mode,
      trumpSuit: trumpSuit,
      currentRoundTricks: currentRoundTricks,
    )) {
      return true;
    }
  }
  return false;
}

/// Check if hand is eligible for Kawesh (redeal).
/// Hand must have NO court cards (A, K, Q, J, 10).
bool canDeclareKawesh(List<CardModel> hand) {
  const courtCards = [Rank.ace, Rank.king, Rank.queen, Rank.jack, Rank.ten];
  return !hand.any((c) => courtCards.contains(c.rank));
}
