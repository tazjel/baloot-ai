/// akkaUtils.dart — Akka (Boss Card) declaration and Kawesh (redeal) logic.
///
/// Port of frontend/src/utils/akkaUtils.ts
///
/// **Akka** (أكّة): A HOKUM-only declaration where the leading player reveals
/// that their card is the highest remaining card of its non-trump suit.
/// This guarantees the trick win and earns bonus points.
///
/// **Kawesh** (كويش): A pre-bid declaration that a hand contains NO court
/// cards (no A, K, Q, J, or 10), entitling the player to a redeal.
library;
import '../models/card_model.dart';
import '../models/enums.dart';
import '../core/constants.dart';

/// Creates a consistent string key for a card (e.g., "A♠", "K♥").
///
/// Accepts [CardModel], [Map] (from JSON), or nested maps with a 'card' key.
/// Returns an empty string for null or unrecognizable inputs.
/// Used for set-based lookups when tracking played cards.
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

/// Builds a [Set] of card key strings for all cards played this round.
///
/// Combines cards from completed [currentRoundTricks] and the current
/// [tableCards] (cards on the table for the trick in progress).
/// Each card is converted to its string key via [cardKey].
///
/// Used by [canDeclareAkka] to check which higher-ranked cards have
/// already been played (and thus cannot beat the candidate card).
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

/// Checks if [card] qualifies for an Akka (Boss Card) declaration.
///
/// All five conditions must be met:
/// 1. **HOKUM only** — Akka doesn't exist in SUN mode.
/// 2. **Leading** — Table must be empty (you must be the trick leader).
/// 3. **Non-trump suit** — Card's suit must NOT be the trump suit.
/// 4. **Not an Ace** — Aces are inherently the boss; no declaration needed.
/// 5. **Highest remaining** — Every card of the same suit that outranks
///    this card must have already been played (checked via [buildPlayedCardsSet])
///    or be held in the player's own hand (which means it's not akka-eligible
///    since you could just play the higher card).
///
/// Returns `true` if the card is eligible for Akka declaration.
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

/// Scans the entire [hand] for any card eligible for Akka declaration.
///
/// Returns `true` if at least one card in the hand passes [canDeclareAkka].
/// Used to show/hide the Akka action button in the UI.
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

/// Checks if [hand] is eligible for Kawesh (كويش) redeal declaration.
///
/// A hand qualifies for Kawesh if it contains NO court cards: no Aces,
/// Kings, Queens, Jacks, or Tens. In other words, the hand consists
/// entirely of 7s, 8s, and 9s — a truly worthless hand.
///
/// Kawesh can be declared pre-bid (no dealer rotation) or post-bid
/// (dealer rotates). The rules for when it can be called are handled
/// by the game state manager, not this function.
bool canDeclareKawesh(List<CardModel> hand) {
  const courtCards = [Rank.ace, Rank.king, Rank.queen, Rank.jack, Rank.ten];
  return !hand.any((c) => courtCards.contains(c.rank));
}

/// Checks if [hand] contains both King and Queen of [trumpSuit] (Baloot).
///
/// Baloot is a special declaration in HOKUM mode worth 2 GP. It can only
/// be declared when the player plays either the K or Q of trump.
/// Returns `true` if both K and Q of trump are present in hand.
bool hasBalootInHand(List<CardModel> hand, Suit? trumpSuit) {
  if (trumpSuit == null) return false;
  final hasKing = hand.any((c) => c.rank == Rank.king && c.suit == trumpSuit);
  final hasQueen = hand.any((c) => c.rank == Rank.queen && c.suit == trumpSuit);
  return hasKing && hasQueen;
}
