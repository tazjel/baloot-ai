import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../state/ui/emote_notifier.dart';
import '../core/theme/colors.dart';
import 'glass_panel_widget.dart';

/// Emote picker menu overlay.
class EmoteMenuWidget extends ConsumerWidget {
  const EmoteMenuWidget({super.key});

  static const _emojis = ['😂', '😎', '🔥', '💪', '👏', '😡', '☕', '🫖', '🌴'];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOpen = ref.watch(emoteProvider.select((s) => s.isMenuOpen));

    if (!isOpen) return const SizedBox.shrink();

    return Stack(
      children: [
        // Dismiss barrier
        Positioned.fill(
          child: GestureDetector(
            onTap: () => ref.read(emoteProvider.notifier).closeMenu(),
            behavior: HitTestBehavior.opaque,
            child: Container(color: Colors.transparent),
          ),
        ),
        // Menu content
        Positioned(
          bottom: 100,
          right: 20,
          child: GlassPanelWidget(
            tint: AppColors.darkSurface,
            opacity: 0.9,
            borderRadius: 16,
            child: Container(
              width: 220,
              padding: const EdgeInsets.all(16),
              child: Wrap(
                spacing: 16,
                runSpacing: 16,
                alignment: WrapAlignment.center,
                children: _emojis.map((emoji) => _EmoteButton(emoji: emoji)).toList(),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _EmoteButton extends ConsumerWidget {
  final String emoji;

  const _EmoteButton({required this.emoji});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GestureDetector(
      onTap: () {
        ref.read(emoteProvider.notifier).sendEmote(emoji);
      },
      child: Container(
        width: 48,
        height: 48,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: AppColors.darkBg.withOpacity(0.5),
          shape: BoxShape.circle,
          border: Border.all(color: AppColors.goldMuted.withOpacity(0.3)),
        ),
        child: Text(
          emoji,
          style: const TextStyle(fontSize: 24),
        ),
      ),
    );
  }
}
