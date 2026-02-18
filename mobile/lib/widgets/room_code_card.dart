/// room_code_card.dart — Shareable room code display with clipboard copy.
///
/// Reusable card widget showing the room code prominently with:
/// - Large monospace room code text
/// - Copy-to-clipboard button with visual feedback
/// - Arabic instruction text
library;
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme/colors.dart';

/// Displays a room code in a prominent card with a copy button.
///
/// Used in the multiplayer lobby to let the host share the room code.
class RoomCodeCard extends StatefulWidget {
  final String roomCode;

  const RoomCodeCard({required this.roomCode, super.key});

  @override
  State<RoomCodeCard> createState() => _RoomCodeCardState();
}

class _RoomCodeCardState extends State<RoomCodeCard> {
  bool _copied = false;
  Timer? _resetTimer;

  @override
  void dispose() {
    _resetTimer?.cancel();
    super.dispose();
  }

  void _copyToClipboard() {
    Clipboard.setData(ClipboardData(text: widget.roomCode));
    HapticFeedback.lightImpact();

    setState(() => _copied = true);
    _resetTimer?.cancel();
    _resetTimer = Timer(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.goldPrimary, width: 1.5),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          const Text(
            'رمز الغرفة',
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 12),

          // Room code + copy button
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SelectableText(
                widget.roomCode,
                style: const TextStyle(
                  fontSize: 32,
                  letterSpacing: 4,
                  fontFamily: 'monospace',
                  fontWeight: FontWeight.bold,
                  color: AppColors.goldPrimary,
                ),
              ),
              const SizedBox(width: 12),
              IconButton(
                icon: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  child: _copied
                      ? const Icon(
                          Icons.check_rounded,
                          key: ValueKey('check'),
                          color: AppColors.success,
                        )
                      : const Icon(
                          Icons.copy_rounded,
                          key: ValueKey('copy'),
                          color: AppColors.goldPrimary,
                        ),
                ),
                tooltip: 'نسخ الرمز',
                onPressed: _copyToClipboard,
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Instruction text
          const Text(
            'شارك الرمز مع أصدقائك',
            style: TextStyle(color: AppColors.textMuted, fontSize: 13),
          ),
          const SizedBox(height: 4),
          const Text(
            'انسخ الرمز وأرسله لصديقك',
            style: TextStyle(color: AppColors.textMuted, fontSize: 11),
          ),
        ],
      ),
    );
  }
}
