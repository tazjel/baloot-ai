/// connection_banner.dart — Disconnected/reconnecting top bar.
///
/// Port of frontend/src/components/ConnectionBanner.tsx
///
/// Shows a banner at the top of the screen when:
/// - Disconnected: red banner with warning
/// - Reconnecting: amber banner with spinner
/// - Connected: banner fades away
library;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/colors.dart';
import '../services/socket_service.dart';
import '../state/ui/connection_status_notifier.dart';

/// Top banner showing connection status when not connected.
class ConnectionBanner extends ConsumerWidget {
  const ConnectionBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(connectionStatusProvider);

    // Only show when disconnected or reconnecting
    if (status == ConnectionStatus.connected) {
      return const SizedBox.shrink();
    }

    final isReconnecting = status == ConnectionStatus.reconnecting;
    final color = isReconnecting ? AppColors.warning : AppColors.error;
    final icon = isReconnecting ? Icons.sync_rounded : Icons.wifi_off_rounded;
    final text = isReconnecting ? 'جاري إعادة الاتصال...' : 'غير متصل';

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.9),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.3),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: SafeArea(
        bottom: false,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isReconnecting)
              const SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            else
              Icon(icon, color: Colors.white, size: 16),
            const SizedBox(width: 8),
            Text(
              text,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
