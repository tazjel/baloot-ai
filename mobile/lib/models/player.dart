/// Player — A game participant (human or bot).
///
/// Port of frontend/src/types.ts Player interface.
library;
import 'card_model.dart';
import 'enums.dart';

class Player {
  final PlayerPosition position;
  final String name;
  final String avatar;
  final List<CardModel> hand;
  final int score;
  final bool isDealer;
  final bool isActive;
  final String? actionText;
  final String? lastReasoning;
  final int index;
  final bool isBot;

  const Player({
    required this.position,
    required this.name,
    this.avatar = '',
    this.hand = const [],
    this.score = 0,
    this.isDealer = false,
    this.isActive = false,
    this.actionText,
    this.lastReasoning,
    required this.index,
    this.isBot = false,
  });

  Player copyWith({
    PlayerPosition? position,
    String? name,
    String? avatar,
    List<CardModel>? hand,
    int? score,
    bool? isDealer,
    bool? isActive,
    String? actionText,
    String? lastReasoning,
    int? index,
    bool? isBot,
  }) {
    return Player(
      position: position ?? this.position,
      name: name ?? this.name,
      avatar: avatar ?? this.avatar,
      hand: hand ?? this.hand,
      score: score ?? this.score,
      isDealer: isDealer ?? this.isDealer,
      isActive: isActive ?? this.isActive,
      actionText: actionText ?? this.actionText,
      lastReasoning: lastReasoning ?? this.lastReasoning,
      index: index ?? this.index,
      isBot: isBot ?? this.isBot,
    );
  }

  factory Player.fromJson(Map<String, dynamic> json) {
    return Player(
      position: PlayerPosition.fromValue(json['position'] as String? ?? 'Bottom'),
      name: json['name'] as String? ?? '',
      avatar: json['avatar'] as String? ?? '',
      hand: (json['hand'] as List<dynamic>?)
              ?.map((c) => CardModel.fromJson(c as Map<String, dynamic>))
              .toList() ??
          [],
      score: json['score'] as int? ?? 0,
      isDealer: json['isDealer'] as bool? ?? false,
      isActive: json['isActive'] as bool? ?? false,
      actionText: json['actionText'] as String?,
      lastReasoning: json['lastReasoning'] as String?,
      index: json['index'] as int? ?? 0,
      isBot: json['is_bot'] as bool? ?? json['isBot'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'position': position.value,
        'name': name,
        'avatar': avatar,
        'hand': hand.map((c) => c.toJson()).toList(),
        'score': score,
        'isDealer': isDealer,
        'isActive': isActive,
        if (actionText != null) 'actionText': actionText,
        if (lastReasoning != null) 'lastReasoning': lastReasoning,
        'index': index,
        'isBot': isBot,
      };
}
