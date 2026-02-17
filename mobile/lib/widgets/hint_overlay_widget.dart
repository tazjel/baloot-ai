import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../state/ui/hint_notifier.dart';
import '../core/theme/colors.dart';
import 'glass_panel_widget.dart';

/// Overlay displaying AI hint reasoning.
class HintOverlayWidget extends ConsumerWidget {
  const HintOverlayWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hintState = ref.watch(hintProvider);
    final isActive = hintState.isActive && hintState.reasoning != null;

    if (!isActive) return const SizedBox.shrink();

    return Align(
      alignment: Alignment.bottomCenter,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 160, left: 20, right: 20),
        child: GlassPanelWidget(
          opacity: 0.9,
          tint: AppColors.darkSurface,
          borderRadius: 12,
          child: Container(
            padding: const EdgeInsets.all(16),
            constraints: const BoxConstraints(maxWidth: 400),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.lightbulb_outline, color: AppColors.goldPrimary),
                    SizedBox(width: 8),
                    Text(
                      'اقتراح الذكاء الاصطناعي',
                      style: TextStyle(
                        color: AppColors.goldPrimary,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  hintState.reasoning!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: AppColors.textLight,
                    fontSize: 14,
                    height: 1.4,
                  ),
                  textDirection: TextDirection.rtl,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
