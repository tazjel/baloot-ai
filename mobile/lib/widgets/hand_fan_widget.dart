/// hand_fan_widget.dart — Bottom card fan for the human player.
///
/// Port of frontend/src/components/HandFan.tsx
///
/// Displays the player's hand as a fanned arc of cards at the bottom
/// of the game board. Supports:
/// - Fan layout with overlapping cards and slight rotation
/// - Tap to select a card (lifts it up)
/// - Tap selected card again to play it
/// - Grayed out cards that aren't legal moves
/// - Trump suit glow
/// - AI hint highlight
library;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../animations/card_animations.dart';
import '../models/card_model.dart';
import '../models/enums.dart';
import '../state/providers.dart';
import 'card_widget.dart';

/// The bottom card fan showing the human player's hand.
///
/// Cards are laid out in a horizontal fan with slight rotation and overlap.
/// Tapping a legal card selects it (lifts up). Tapping again plays it.
class HandFanWidget extends ConsumerStatefulWidget {
  const HandFanWidget({super.key});

  @override
  ConsumerState<HandFanWidget> createState() => _HandFanWidgetState();
}

class _HandFanWidgetState extends ConsumerState<HandFanWidget> {
  /// Index of currently selected card (-1 = none).
  int _selectedIndex = -1;

  /// Track previous hand count to detect new deal.
  int _prevHandCount = 0;

  /// Whether to play deal animation on current hand.
  bool _needsDealAnimation = false;

  @override
  Widget build(BuildContext context) {
    final appState = ref.watch(gameStateProvider);
    final gameState = appState.gameState;
    final rules = ref.watch(gameRulesProvider);
    final hand = gameState.myHand;
    final isMyTurn = rules.isMyTurn;
    final legalIndices = rules.legalCardIndices;
    final trumpSuit = rules.trumpSuit;
    final isTrickTransitioning = rules.isTrickTransitioning;

    // Don't show if no cards or waiting phase
    if (hand.isEmpty || gameState.phase == GamePhase.waiting) {
      _prevHandCount = 0;
      return const SizedBox.shrink();
    }

    // Detect new deal: hand jumped from 0 to full (8 cards)
    if (hand.length >= 7 && _prevHandCount == 0) {
      _needsDealAnimation = true;
    }
    _prevHandCount = hand.length;

    return LayoutBuilder(
      builder: (context, constraints) {
        final availableWidth = constraints.maxWidth;
        final cardCount = hand.length;

        // Dynamic card sizing
        final cardWidth = (availableWidth * 0.11).clamp(40.0, 62.0);
        final cardHeight = cardWidth * 1.4;

        // Fan overlap: ensure all cards fit within available width
        final totalCardWidth = cardWidth * cardCount;
        final overlap = cardCount > 1
            ? ((totalCardWidth - availableWidth * 0.85) / (cardCount - 1))
                .clamp(0.0, cardWidth * 0.55)
            : 0.0;
        final effectiveCardWidth = cardWidth - overlap;
        final fanWidth = effectiveCardWidth * (cardCount - 1) + cardWidth;
        final startX = (availableWidth - fanWidth) / 2;

        // Fan rotation: slight angle per card
        final maxAngle = cardCount <= 4 ? 3.0 : 5.0; // degrees
        final angleStep =
            cardCount > 1 ? (maxAngle * 2) / (cardCount - 1) : 0.0;

        return SizedBox(
          height: cardHeight + 24, // Extra room for lift animation
          child: Stack(
            clipBehavior: Clip.none,
            children: List.generate(cardCount, (i) {
              final card = hand[i];
              final isLegal =
                  isMyTurn && legalIndices.contains(i) && !isTrickTransitioning;
              final isSelected = _selectedIndex == i;
              final isTrump = trumpSuit != null && card.suit == trumpSuit;
              final isOtherCard = !isLegal &&
                  isMyTurn &&
                  gameState.phase == GamePhase.playing;

              // Position
              final xPos = startX + i * effectiveCardWidth;
              final angle = cardCount > 1
                  ? (-maxAngle + i * angleStep) * 3.14159 / 180
                  : 0.0;

              // Lift selected card
              final yOffset = isSelected ? -18.0 : 0.0;

              Widget cardChild = Opacity(
                opacity: isOtherCard ? 0.5 : 1.0,
                child: CardWidget(
                  card: card,
                  width: cardWidth,
                  isSelected: isSelected,
                  isPlayable: isLegal,
                  isTrump: isTrump,
                  onTap: isLegal
                      ? () => _onCardTap(i, card)
                      : null,
                ),
              );

              // Wrap with deal animation on new deal
              if (_needsDealAnimation) {
                cardChild = AnimatedCardDeal(
                  staggerIndex: i,
                  onComplete: i == cardCount - 1
                      ? () {
                          if (mounted) {
                            setState(() => _needsDealAnimation = false);
                          }
                        }
                      : null,
                  child: cardChild,
                );
              }

              return Positioned(
                left: xPos,
                bottom: 4 + yOffset,
                child: Transform.rotate(
                  angle: angle,
                  alignment: Alignment.bottomCenter,
                  child: cardChild,
                ),
              );
            }),
          ),
        );
      },
    );
  }

  void _onCardTap(int index, CardModel card) {
    if (_selectedIndex == index) {
      // Second tap on selected card → play it
      HapticFeedback.mediumImpact();
      _playCard(index);
    } else {
      // First tap → select
      HapticFeedback.selectionClick();
      setState(() => _selectedIndex = index);
    }
  }

  void _playCard(int index) {
    setState(() => _selectedIndex = -1);
    // Dispatch play action
    ref
        .read(gameStateProvider.notifier)
        .addSystemMessage('لعبت ${ref.read(gameStateProvider).gameState.myHand[index]}');

    // Use action dispatcher to play card
    ref.read(actionDispatcherProvider.notifier).handlePlayerAction(
      'PLAY',
      payload: {'cardIndex': index},
    );
  }
}
