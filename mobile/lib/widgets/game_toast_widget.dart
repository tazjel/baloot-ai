import 'package:flutter/material.dart';
import '../core/theme/colors.dart';
import '../state/ui/toast_notifier.dart';

/// Single toast notification card.
class GameToastWidget extends StatelessWidget {
  final ToastMessage toast;
  final VoidCallback onDismiss;

  const GameToastWidget({
    super.key,
    required this.toast,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final config = _getConfig(toast.type);

    return Dismissible(
      key: Key(toast.id),
      onDismissed: (_) => onDismiss(),
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.darkSurface.withOpacity(0.95),
          border: BorderDirectional(start: BorderSide(color: config.color, width: 4)),
          borderRadius: BorderRadius.circular(8),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 4),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(config.icon, color: config.color, size: 20),
            const SizedBox(width: 12),
            Flexible(
              child: Text(
                toast.message,
                style: const TextStyle(
                  color: AppColors.textLight,
                  fontSize: 14,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  _ToastConfig _getConfig(ToastType type) {
    switch (type) {
      case ToastType.turn:
        return _ToastConfig(AppColors.goldPrimary, Icons.play_arrow_rounded);
      case ToastType.akka:
        return _ToastConfig(AppColors.error, Icons.flash_on_rounded);
      case ToastType.sawa:
        return _ToastConfig(AppColors.warning, Icons.handshake_rounded);
      case ToastType.project:
        return _ToastConfig(AppColors.goldPrimary, Icons.star_rounded);
      case ToastType.trick:
        return _ToastConfig(AppColors.success, Icons.check_circle_rounded);
      case ToastType.baloot:
        return _ToastConfig(AppColors.goldPrimary, Icons.workspace_premium_rounded);
      case ToastType.kaboot:
        return _ToastConfig(AppColors.goldPrimary, Icons.local_fire_department_rounded);
      case ToastType.success:
        return _ToastConfig(AppColors.success, Icons.check_circle_outline_rounded);
      case ToastType.error:
        return _ToastConfig(AppColors.error, Icons.error_outline_rounded);
      case ToastType.warning:
        return _ToastConfig(AppColors.warning, Icons.warning_amber_rounded);
      case ToastType.info:
      default:
        return _ToastConfig(AppColors.info, Icons.info_outline_rounded);
    }
  }
}

class _ToastConfig {
  final Color color;
  final IconData icon;
  _ToastConfig(this.color, this.icon);
}
