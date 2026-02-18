/// DeclaredProject — A declared Mashaari or Baloot project.
library;
import 'card_model.dart';
import 'enums.dart';

class DeclaredProject {
  final ProjectType type;
  final Rank rank;
  final Suit suit;
  final PlayerPosition owner;
  final int? score;
  final List<CardModel>? cards;

  const DeclaredProject({
    required this.type,
    required this.rank,
    required this.suit,
    required this.owner,
    this.score,
    this.cards,
  });

  factory DeclaredProject.fromJson(Map<String, dynamic> json) {
    return DeclaredProject(
      type: ProjectType.fromValue(json['type'] as String),
      rank: Rank.fromSymbol(json['rank'] as String),
      suit: Suit.fromSymbol(json['suit'] as String),
      owner: PlayerPosition.fromValue(json['owner'] as String),
      score: json['score'] as int?,
      cards: (json['cards'] as List<dynamic>?)
          ?.map((c) => CardModel.fromJson(c as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'type': type.value,
        'rank': rank.symbol,
        'suit': suit.symbol,
        'owner': owner.value,
        if (score != null) 'score': score,
        if (cards != null) 'cards': cards!.map((c) => c.toJson()).toList(),
      };
}
