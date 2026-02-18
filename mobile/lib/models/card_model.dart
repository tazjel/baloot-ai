/// CardModel — A single playing card.
///
/// Port of frontend/src/types.ts CardModel interface.
library;
import 'enums.dart';

class CardModel {
  final String id;
  final Suit suit;
  final Rank rank;
  final int value;

  const CardModel({
    required this.id,
    required this.suit,
    required this.rank,
    this.value = 0,
  });

  /// Create from JSON map (server format)
  factory CardModel.fromJson(Map<String, dynamic> json) {
    return CardModel(
      id: json['id'] as String? ?? '',
      suit: Suit.fromSymbol(json['suit'] as String),
      rank: Rank.fromSymbol(json['rank'] as String),
      value: json['value'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'suit': suit.symbol,
        'rank': rank.symbol,
        'value': value,
      };

  /// Unique key for card identification (e.g., "A♠")
  String get key => '${rank.symbol}${suit.symbol}';

  CardModel copyWith({
    String? id,
    Suit? suit,
    Rank? rank,
    int? value,
  }) {
    return CardModel(
      id: id ?? this.id,
      suit: suit ?? this.suit,
      rank: rank ?? this.rank,
      value: value ?? this.value,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CardModel &&
          runtimeType == other.runtimeType &&
          suit == other.suit &&
          rank == other.rank;

  @override
  int get hashCode => suit.hashCode ^ rank.hashCode;

  @override
  String toString() => '${rank.symbol}${suit.symbol}';
}

/// A card played on the table with metadata
class TableCard {
  final CardModel card;
  final PlayerPosition playedBy;
  final Map<String, dynamic>? metadata;

  const TableCard({
    required this.card,
    required this.playedBy,
    this.metadata,
  });

  bool get isAkka => metadata?['akka'] == true;

  factory TableCard.fromJson(Map<String, dynamic> json) {
    return TableCard(
      card: CardModel.fromJson(
        json['card'] is Map<String, dynamic>
            ? json['card'] as Map<String, dynamic>
            : json,
      ),
      playedBy: PlayerPosition.fromValue(json['playedBy'] as String? ?? 'Bottom'),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() => {
        'card': card.toJson(),
        'playedBy': playedBy.value,
        if (metadata != null) 'metadata': metadata,
      };
}
