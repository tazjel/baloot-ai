import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/colors.dart';
import '../models/card_model.dart';
import '../models/enums.dart';
import '../state/ui/replay_notifier.dart';
import 'card_widget.dart';

class MatchReviewModal extends ConsumerWidget {
  const MatchReviewModal({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final replayState = ref.watch(replayProvider);
    
    if (!replayState.isActive) return const SizedBox.shrink();

    final notifier = ref.read(replayProvider.notifier);
    final currentState = replayState.currentState;

    return Container(
      height: 500,
      decoration: const BoxDecoration(
        color: AppColors.backgroundDark,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
        border: Border(top: BorderSide(color: AppColors.goldPrimary, width: 2)),
      ),
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('إعادة العرض', style: TextStyle(color: AppColors.goldPrimary, fontSize: 20, fontWeight: FontWeight.bold)),
                IconButton(
                  icon: const Icon(Icons.close, color: AppColors.textMuted),
                  onPressed: () => notifier.exitReplay(),
                ),
              ],
            ),
          ),
          const Divider(color: AppColors.primaryWithOpacity),

          // Game Board Viewer
          Expanded(
            child: currentState == null 
              ? const Center(child: Text('لا توجد بيانات', style: TextStyle(color: AppColors.textMuted)))
              : Stack(
                  alignment: Alignment.center,
                  children: [
                    // Table background/felt
                    Container(
                      margin: const EdgeInsets.all(32),
                      decoration: BoxDecoration(
                        color: AppColors.tableGreen.withOpacity(0.5),
                        shape: BoxShape.circle,
                        border: Border.all(color: AppColors.goldPrimary.withOpacity(0.3), width: 2),
                      ),
                    ),

                    // Cards on Table
                    ...currentState.tableCards.map((tc) {
                      return _buildTableCard(tc);
                    }),

                    // Center Info (Scores/Trick Winner?)
                    // Maybe show trick winner if available in lastTrick?
                  ],
                ),
          ),

          // Controls
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.black26,
            child: Column(
              children: [
                // Progress Bar & Step Info
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${replayState.currentIndex + 1} / ${replayState.totalSteps}', 
                      style: const TextStyle(color: AppColors.textLight, fontFamily: 'monospace')
                    ),
                    Text(
                      'خطوة ${replayState.currentIndex}',
                      style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Slider(
                  value: replayState.currentIndex.toDouble(),
                  min: 0,
                  max: (replayState.totalSteps > 0 ? replayState.totalSteps - 1 : 0).toDouble(),
                  activeColor: AppColors.goldPrimary,
                  inactiveColor: AppColors.primaryWithOpacity,
                  onChanged: (val) => notifier.jumpTo(val.toInt()),
                ),

                // Transport Controls
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    // Speed Toggle
                    PopupMenuButton<double>(
                      initialValue: replayState.playbackSpeed,
                      color: AppColors.cardSurface,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          border: Border.all(color: AppColors.textMuted),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Text('${replayState.playbackSpeed.toStringAsFixed(0)}x', style: const TextStyle(color: AppColors.textLight)),
                      ),
                      onSelected: (speed) => notifier.setSpeed(speed),
                      itemBuilder: (context) => [
                        const PopupMenuItem(value: 1.0, child: Text('1x', style: TextStyle(color: Colors.white))),
                        const PopupMenuItem(value: 2.0, child: Text('2x', style: TextStyle(color: Colors.white))),
                        const PopupMenuItem(value: 4.0, child: Text('4x', style: TextStyle(color: Colors.white))),
                      ],
                    ),

                    IconButton(
                      icon: const Icon(Icons.skip_previous, color: Colors.white),
                      onPressed: () => notifier.previous(),
                    ),
                    
                    FloatingActionButton(
                      mini: true,
                      backgroundColor: AppColors.goldPrimary,
                      onPressed: () => notifier.togglePlay(),
                      child: Icon(replayState.isPlaying ? Icons.pause : Icons.play_arrow, color: Colors.black),
                    ),

                    IconButton(
                      icon: const Icon(Icons.skip_next, color: Colors.white),
                      onPressed: () => notifier.next(),
                    ),

                    // Checkbox for "Card Animation"? (Optional)
                     const SizedBox(width: 40), // Balancer
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTableCard(TableCard tableCard) {
    // Determine alignment based on PlayerPosition
    Alignment alignment = Alignment.center;
    double angle = 0;

    switch (tableCard.playedBy) {
      case PlayerPosition.bottom:
        alignment = const Alignment(0, 0.6);
        break;
      case PlayerPosition.right:
        alignment = const Alignment(0.6, 0);
        angle = -1.5708; // -90 deg
        break;
      case PlayerPosition.top:
        alignment = const Alignment(0, -0.6);
        angle = 3.14159; // 180 deg
        break;
      case PlayerPosition.left:
        alignment = const Alignment(-0.6, 0);
        angle = 1.5708; // 90 deg
        break;
    }

    return Align(
      alignment: alignment,
      child: Transform.rotate(
        angle: angle,
        child: CardWidget(
          card: tableCard.card,
          width: 50, // Smaller cards for replay
          isPlayable: false,
        ),
      ),
    );
  }
}
