import 'package:flutter/material.dart';
import '../core/theme/colors.dart';
import '../models/enums.dart';

/// Colored suit symbol display (♠♥♦♣).
class SuitIconWidget extends StatelessWidget {
  final Suit suit;
  final double size;
  const SuitIconWidget({super.key, required this.suit, this.size = 16});

  @override
  Widget build(BuildContext context) {
    return Text(suit.symbol, style: TextStyle(fontSize: size, color: _color));
  }

  Color get _color {
    switch (suit) {
      case Suit.spades: return AppColors.suitSpades;
      case Suit.hearts: return AppColors.suitHearts;
      case Suit.diamonds: return AppColors.suitDiamonds;
      case Suit.clubs: return AppColors.suitClubs;
    }
  }
}
