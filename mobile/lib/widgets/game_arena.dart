/// game_arena.dart — Center play area with table cards and floor card.
///
/// Port of frontend/src/components/GameArena.tsx
///
/// The center of the game board showing:
/// - Table felt background (wood + felt texture)
/// - Floor card during dealing
/// - Played cards in cross formation
/// - Waiting state with "Add Bot" button
///
/// NOTE: Player avatars are rendered by game_screen.dart at absolute
/// screen positions — NOT here. Previously avatars were duplicated in
/// both game_arena and game_screen, causing 7 instances and GPU overload.
library;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../animations/card_animations.dart';
import '../core/theme/colors.dart';
import '../models/card_model.dart';
import '../models/enums.dart';
import '../state/providers.dart';
import 'card_widget.dart';

/// The center play area of the game board.
///
/// Contains the table felt, floor card, and played cards in cross formation.
class GameArena extends ConsumerWidget {
  const GameArena({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appState = ref.watch(gameStateProvider);
    final gameState = appState.gameState;
    final tableCards = gameState.tableCards;
    final floorCard = gameState.floorCard;
    final isWaiting = gameState.phase == GamePhase.waiting;

    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        final h = constraints.maxHeight;
        final cardW = (w * 0.12).clamp(40.0, 65.0);

        return Container(
          width: w,
          height: h,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: const Color(0xFF3E2723).withOpacity(0.6),
              width: 3,
            ),
            gradient: const RadialGradient(
              center: Alignment.center,
              radius: 0.9,
              colors: [
                Color(0xFF1F5C38), // Lighter felt center
                AppColors.tableGreen, // Standard green
                Color(0xFF133220), // Darker edges
              ],
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.4),
                blurRadius: 20,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              // Inner felt inset shadow
              Positioned.fill(
                child: Container(
                  margin: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(21),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.2),
                        blurRadius: 8,
                        spreadRadius: -4,
                      ),
                    ],
                  ),
                ),
              ),

              // Waiting state
              if (isWaiting)
                Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.hourglass_empty,
                        size: 32,
                        color: Colors.white.withOpacity(0.5),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'في انتظار اللاعبين...',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),

              // Floor card (during bidding) — animated 3D flip reveal
              if (floorCard != null && gameState.phase == GamePhase.bidding)
                Center(
                  child: AnimatedFloorReveal(
                    child: Container(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(6),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.goldPrimary.withOpacity(0.4),
                            blurRadius: 16,
                            spreadRadius: 2,
                          ),
                        ],
                      ),
                      child: CardWidget(
                        card: floorCard,
                        width: cardW,
                      ),
                    ),
                  ),
                ),

              // Played cards in cross formation
              if (tableCards.isNotEmpty && !isWaiting)
                ..._buildTableCards(tableCards, w, h, cardW),
            ],
          ),
        );
      },
    );
  }

  /// Build the played cards in cross formation at the center.
  List<Widget> _buildTableCards(
    List<TableCard> tableCards,
    double w,
    double h,
    double cardW,
  ) {
    final centerX = w / 2 - cardW / 2;
    final centerY = h / 2 - cardW * 0.7;
    final offset = cardW * 0.75;

    return tableCards.map((tc) {
      // Position based on which player played the card
      double dx = centerX;
      double dy = centerY;
      switch (tc.playedBy) {
        case PlayerPosition.bottom:
          dy = centerY + offset;
          break;
        case PlayerPosition.top:
          dy = centerY - offset;
          break;
        case PlayerPosition.left:
          dx = centerX - offset;
          break;
        case PlayerPosition.right:
          dx = centerX + offset;
          break;
      }

      return Positioned(
        left: dx,
        top: dy,
        child: AnimatedCardPlay(
          fromPosition: tc.playedBy,
          child: AnimatedThump(
            child: CardWidget(
              card: tc.card,
              width: cardW,
            ),
          ),
        ),
      );
    }).toList();
  }
}
