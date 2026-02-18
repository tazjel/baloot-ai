/// player_avatar_widget.dart — Player info display at table position.
///
/// Port of frontend/src/components/PlayerAvatar.tsx
///
/// Displays player info at one of four table positions:
/// - Avatar circle with initial letter
/// - Player name label
/// - Turn indicator (gold halo when active)
/// - Dealer badge ("D")
/// - Action text (bid announcement)
/// - Speech bubble (bot dialogue)
/// - Score display
library;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../animations/ui_animations.dart';
import '../core/theme/colors.dart';
import '../models/player.dart';
import '../state/audio/bot_speech_notifier.dart';

/// Displays a player's avatar, name, and status at their table position.
class PlayerAvatarWidget extends ConsumerWidget {
  /// The player to display.
  final Player player;

  /// The seat index (0-3).
  final int index;

  /// Whether it's this player's turn.
  final bool isCurrentTurn;

  /// Remaining time for turn timer (0-1 fraction).
  final double? timerFraction;

  /// Size scale factor (default 1.0).
  final double scale;

  const PlayerAvatarWidget({
    super.key,
    required this.player,
    required this.index,
    this.isCurrentTurn = false,
    this.timerFraction,
    this.scale = 1.0,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final speechState = ref.watch(botSpeechProvider);
    final isSpeaking =
        speechState.isSpeaking && speechState.speakerIndex == index;
    final avatarSize = 40.0 * scale;
    final nameSize = 11.0 * scale;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Speech bubble — animated fade in/out
        if (isSpeaking && speechState.currentText != null)
          AnimatedSpeechBubble(
            child: _SpeechBubble(
              text: speechState.currentText!,
              scale: scale,
            ),
          ),

        // Avatar circle + turn indicator (pulsing when active)
        _maybePulse(
          isCurrentTurn,
          Stack(
          alignment: Alignment.center,
          children: [
            // Turn halo
            if (isCurrentTurn)
              Container(
                width: avatarSize + 12,
                height: avatarSize + 12,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: AppColors.goldPrimary.withOpacity(0.7),
                    width: 2.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.goldPrimary.withOpacity(0.3),
                      blurRadius: 12,
                      spreadRadius: 2,
                    ),
                  ],
                ),
              ),

            // Timer ring
            if (isCurrentTurn && timerFraction != null)
              SizedBox(
                width: avatarSize + 12,
                height: avatarSize + 12,
                child: CircularProgressIndicator(
                  value: timerFraction,
                  strokeWidth: 2.5,
                  color: (timerFraction! < 0.3)
                      ? AppColors.error
                      : AppColors.goldPrimary,
                  backgroundColor: Colors.white.withOpacity(0.1),
                ),
              ),

            // Avatar circle
            Container(
              width: avatarSize,
              height: avatarSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _avatarColor(index),
                border: Border.all(
                  color: isCurrentTurn
                      ? AppColors.goldPrimary
                      : Colors.white.withOpacity(0.3),
                  width: isCurrentTurn ? 2 : 1,
                ),
              ),
              child: Center(
                child: Text(
                  player.name.isNotEmpty
                      ? player.name.substring(0, 1).toUpperCase()
                      : '?',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: avatarSize * 0.4,
                  ),
                ),
              ),
            ),

            // Dealer badge
            if (player.isDealer)
              Positioned(
                bottom: 0,
                right: 0,
                child: Container(
                  width: 16 * scale,
                  height: 16 * scale,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.goldPrimary,
                  ),
                  child: Center(
                    child: Text(
                      'D',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 9 * scale,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
        ),

        SizedBox(height: 3 * scale),

        // Player name
        Container(
          padding: EdgeInsets.symmetric(
            horizontal: 6 * scale,
            vertical: 2 * scale,
          ),
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(0.5),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            player.name,
            style: TextStyle(
              color: Colors.white,
              fontSize: nameSize,
              fontWeight: FontWeight.w500,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),

        // Action text (bid announcement)
        if (player.actionText != null) ...[
          SizedBox(height: 2 * scale),
          Container(
            padding: EdgeInsets.symmetric(
              horizontal: 8 * scale,
              vertical: 3 * scale,
            ),
            decoration: BoxDecoration(
              color: _actionColor(player.actionText!),
              borderRadius: BorderRadius.circular(8),
              boxShadow: [
                BoxShadow(
                  color: _actionColor(player.actionText!).withOpacity(0.4),
                  blurRadius: 4,
                ),
              ],
            ),
            child: Text(
              player.actionText!,
              style: TextStyle(
                color: Colors.white,
                fontSize: 10 * scale,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ],
    );
  }

  Color _avatarColor(int idx) {
    const colors = [
      Color(0xFF3B82F6), // Blue (human)
      Color(0xFFEF4444), // Red (opponent)
      Color(0xFF22C55E), // Green (partner)
      Color(0xFFF59E0B), // Amber (opponent)
    ];
    return colors[idx % colors.length];
  }

  /// Wraps child with pulse animation when it's this player's turn.
  Widget _maybePulse(bool isActive, Widget child) {
    if (isActive) {
      return TurnIndicatorPulse(child: child);
    }
    return child;
  }

  Color _actionColor(String action) {
    if (action == 'صن' || action == 'أشكال') return AppColors.info;
    if (action == 'حكم') return AppColors.error;
    if (action == 'بس') return Colors.grey.shade700;
    return AppColors.goldPrimary;
  }
}

/// Bot speech bubble widget.
class _SpeechBubble extends StatelessWidget {
  final String text;
  final double scale;

  const _SpeechBubble({required this.text, required this.scale});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: EdgeInsets.only(bottom: 6 * scale),
      padding: EdgeInsets.symmetric(
        horizontal: 10 * scale,
        vertical: 6 * scale,
      ),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Text(
        text,
        style: TextStyle(
          color: Colors.black87,
          fontSize: 11 * scale,
        ),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}
