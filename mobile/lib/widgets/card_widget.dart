/// card_widget.dart — Individual playing card renderer.
///
/// Port of frontend/src/components/Card.tsx
///
/// Renders a single Baloot playing card with:
/// - Rank and suit in top-left and bottom-right corners
/// - Pip layout for number cards (7-10)
/// - Large suit icon for Ace and face cards (J/Q/K)
/// - Card back with optional skin texture
/// - Selected state (gold ring + lift)
/// - Playable hover state
/// - Trump suit glow effect
import 'package:flutter/material.dart';

import '../core/theme/colors.dart';
import '../models/card_model.dart';
import '../models/enums.dart';

/// Widget that renders a single playing card.
///
/// Supports face-up display with rank/suit, face-down (back),
/// selection highlight, playable hover, and trump glow.
class CardWidget extends StatelessWidget {
  /// The card to render.
  final CardModel card;

  /// Whether this card is selected (gold ring + lift).
  final bool isSelected;

  /// Whether the card is face-down.
  final bool isHidden;

  /// Whether the card is playable (enables hover effect).
  final bool isPlayable;

  /// Whether this card is the trump suit (glow effect).
  final bool isTrump;

  /// Whether this card is hinted by AI (pulse glow).
  final bool isHinted;

  /// Card width (height = width * 1.4).
  final double width;

  /// Callback when the card is tapped.
  final VoidCallback? onTap;

  const CardWidget({
    super.key,
    required this.card,
    this.isSelected = false,
    this.isHidden = false,
    this.isPlayable = false,
    this.isTrump = false,
    this.isHinted = false,
    this.width = 60,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final height = width * 1.4;
    final suitColor = _suitColor(card.suit);
    final suitSymbol = card.suit.symbol;
    final rankStr = card.rank.symbol;
    final fontSize = width * 0.22;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: isHidden ? AppColors.cardBack : Colors.white,
          borderRadius: BorderRadius.circular(width * 0.1),
          border: Border.all(
            color: isSelected
                ? AppColors.goldPrimary
                : isHinted
                    ? AppColors.info
                    : Colors.grey.shade300,
            width: isSelected ? 2.5 : 1,
          ),
          boxShadow: [
            if (isSelected)
              BoxShadow(
                color: AppColors.goldPrimary.withOpacity(0.5),
                blurRadius: 8,
                spreadRadius: 1,
              ),
            if (isHinted)
              BoxShadow(
                color: AppColors.info.withOpacity(0.5),
                blurRadius: 12,
                spreadRadius: 2,
              ),
            if (isTrump && !isHidden)
              BoxShadow(
                color: suitColor.withOpacity(0.3),
                blurRadius: 6,
                spreadRadius: 1,
              ),
            BoxShadow(
              color: Colors.black.withOpacity(0.15),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: isHidden ? _buildBack() : _buildFace(suitColor, suitSymbol, rankStr, fontSize),
      ),
    );
  }

  /// Build the card back (face-down).
  Widget _buildBack() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(width * 0.1),
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              AppColors.cardBack,
              AppColors.cardBack.withOpacity(0.8),
              AppColors.cardBack,
            ],
          ),
        ),
        child: Center(
          child: Container(
            width: width * 0.6,
            height: width * 0.6,
            decoration: BoxDecoration(
              border: Border.all(color: AppColors.goldPrimary.withOpacity(0.4), width: 1.5),
              borderRadius: BorderRadius.circular(width * 0.08),
            ),
            child: Center(
              child: Text(
                '\u2660', // Spade symbol as decoration
                style: TextStyle(
                  fontSize: width * 0.3,
                  color: AppColors.goldPrimary.withOpacity(0.3),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// Build the card face (face-up).
  Widget _buildFace(Color suitColor, String suitSymbol, String rankStr, double fontSize) {
    return Padding(
      padding: EdgeInsets.all(width * 0.06),
      child: Stack(
        children: [
          // Top-left index
          Positioned(
            top: 0,
            left: 0,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  rankStr,
                  style: TextStyle(
                    fontSize: fontSize,
                    fontWeight: FontWeight.bold,
                    color: suitColor,
                    height: 1.0,
                  ),
                ),
                Text(
                  suitSymbol,
                  style: TextStyle(
                    fontSize: fontSize * 0.85,
                    color: suitColor,
                    height: 1.0,
                  ),
                ),
              ],
            ),
          ),

          // Bottom-right index (rotated 180)
          Positioned(
            bottom: 0,
            right: 0,
            child: Transform.rotate(
              angle: 3.14159, // 180 degrees
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    rankStr,
                    style: TextStyle(
                      fontSize: fontSize,
                      fontWeight: FontWeight.bold,
                      color: suitColor,
                      height: 1.0,
                    ),
                  ),
                  Text(
                    suitSymbol,
                    style: TextStyle(
                      fontSize: fontSize * 0.85,
                      color: suitColor,
                      height: 1.0,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Center content
          Center(
            child: _buildCenterContent(suitColor, suitSymbol),
          ),
        ],
      ),
    );
  }

  /// Build the center content based on rank.
  Widget _buildCenterContent(Color suitColor, String suitSymbol) {
    final rank = card.rank;
    final centerSize = width * 0.35;

    // Ace: large suit icon
    if (rank == Rank.ace) {
      return Text(
        suitSymbol,
        style: TextStyle(fontSize: centerSize, color: suitColor),
      );
    }

    // Face cards (J/Q/K): medium suit icon with letter
    if (rank == Rank.jack || rank == Rank.queen || rank == Rank.king) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            suitSymbol,
            style: TextStyle(fontSize: centerSize * 0.7, color: suitColor),
          ),
          Text(
            rank.symbol,
            style: TextStyle(
              fontSize: centerSize * 0.5,
              fontWeight: FontWeight.bold,
              color: suitColor.withOpacity(0.6),
            ),
          ),
        ],
      );
    }

    // Number cards (7-10): pip grid
    return _buildPipGrid(suitColor, suitSymbol);
  }

  /// Build pip layout for number cards.
  Widget _buildPipGrid(Color suitColor, String suitSymbol) {
    final pipSize = width * 0.18;
    final pipCount = _rankToPipCount(card.rank);

    return Wrap(
      alignment: WrapAlignment.center,
      spacing: width * 0.04,
      runSpacing: width * 0.02,
      children: List.generate(
        pipCount,
        (_) => Text(
          suitSymbol,
          style: TextStyle(fontSize: pipSize, color: suitColor),
        ),
      ),
    );
  }

  int _rankToPipCount(Rank rank) {
    switch (rank) {
      case Rank.seven:
        return 5;
      case Rank.eight:
        return 6;
      case Rank.nine:
        return 7;
      case Rank.ten:
        return 8;
      default:
        return 1;
    }
  }

  Color _suitColor(Suit suit) {
    switch (suit) {
      case Suit.spades:
        return AppColors.suitSpades;
      case Suit.hearts:
        return AppColors.suitHearts;
      case Suit.diamonds:
        return AppColors.suitDiamonds;
      case Suit.clubs:
        return AppColors.suitClubs;
    }
  }
}
