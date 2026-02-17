import 'enums.dart';

class HintResult {
  final String action;
  final int? cardIndex;
  final Suit? suit;
  final String reasoning;

  const HintResult({
    required this.action,
    this.cardIndex,
    this.suit,
    required this.reasoning,
  });

  factory HintResult.fromJson(Map<String, dynamic> json) {
    return HintResult(
      action: json['action'] as String,
      cardIndex: json['cardIndex'] as int?,
      suit: json['suit'] != null ? Suit.fromSymbol(json['suit'] as String) : null,
      reasoning: json['reasoning'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
        'action': action,
        if (cardIndex != null) 'cardIndex': cardIndex,
        if (suit != null) 'suit': suit!.symbol,
        'reasoning': reasoning,
      };

  @override
  String toString() {
    return 'HintResult(action: $action, cardIndex: $cardIndex, suit: $suit, reasoning: $reasoning)';
  }
}
