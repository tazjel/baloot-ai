import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../animations/ui_animations.dart';
import '../state/ui/toast_notifier.dart';

class ToastOverlay extends ConsumerWidget {
  const ToastOverlay({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final toasts = ref.watch(toastProvider);

    if (toasts.isEmpty) return const SizedBox.shrink();

    return Positioned(
      top: 60,
      left: 20,
      right: 20,
      child: Column(
        children: toasts.map((toast) {
          return AnimatedToastEntry(
            key: Key('anim-${toast.id}'),
            onDismiss: () => ref.read(toastProvider.notifier).remove(toast.id),
            child: Dismissible(
              key: Key(toast.id),
              onDismissed: (_) {
                ref.read(toastProvider.notifier).remove(toast.id);
              },
              child: Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: _getColor(toast.type).withOpacity(0.9),
                borderRadius: BorderRadius.circular(8),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Icon(_getIcon(toast.type), color: Colors.white, size: 20),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      toast.message,
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white70, size: 16),
                    onPressed: () => ref.read(toastProvider.notifier).remove(toast.id),
                  ),
                ],
              ),
            ),
          ),
          );
        }).toList(),
      ),
    );
  }

  Color _getColor(ToastType type) {
    switch (type) {
      case ToastType.success: return Colors.green[700]!;
      case ToastType.error: return Colors.red[700]!;
      case ToastType.warning: return Colors.orange[800]!;
      case ToastType.project: return Colors.indigo[600]!;
      case ToastType.info:
      default: return Colors.black87;
    }
  }

  IconData _getIcon(ToastType type) {
    switch (type) {
      case ToastType.success: return Icons.check_circle;
      case ToastType.error: return Icons.error_outline;
      case ToastType.warning: return Icons.warning_amber_rounded;
      case ToastType.project: return Icons.smart_toy;
      case ToastType.info:
      default: return Icons.info_outline;
    }
  }
}
