/// Bid — Current round bid state.
import 'enums.dart';

class Bid {
  final GameMode? type;
  final Suit? suit;
  final PlayerPosition? bidder;
  final bool doubled;

  const Bid({
    this.type,
    this.suit,
    this.bidder,
    this.doubled = false,
  });

  const Bid.empty()
      : type = null,
        suit = null,
        bidder = null,
        doubled = false;

  Bid copyWith({
    GameMode? type,
    Suit? suit,
    PlayerPosition? bidder,
    bool? doubled,
  }) {
    return Bid(
      type: type ?? this.type,
      suit: suit ?? this.suit,
      bidder: bidder ?? this.bidder,
      doubled: doubled ?? this.doubled,
    );
  }

  factory Bid.fromJson(Map<String, dynamic> json) {
    return Bid(
      type: json['type'] != null ? GameMode.fromValue(json['type'] as String) : null,
      suit: json['suit'] != null ? Suit.fromSymbol(json['suit'] as String) : null,
      bidder: json['bidder'] != null
          ? PlayerPosition.fromValue(json['bidder'] as String)
          : null,
      doubled: json['doubled'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'type': type?.value,
        'suit': suit?.symbol,
        'bidder': bidder?.value,
        'doubled': doubled,
      };
}
