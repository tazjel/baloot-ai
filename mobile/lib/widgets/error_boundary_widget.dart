import 'package:flutter/material.dart';
import '../core/theme/colors.dart';

/// Global error handler widget replacing the default "Red Screen of Death".
class ErrorBoundaryWidget extends StatelessWidget {
  final FlutterErrorDetails details;

  const ErrorBoundaryWidget({super.key, required this.details});

  /// Initialize the global error widget builder.
  /// Call this in main() before runApp().
  static void initialize() {
    ErrorWidget.builder = (details) => ErrorBoundaryWidget(details: details);
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.darkBg,
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline_rounded,
              color: AppColors.error,
              size: 64,
            ),
            const SizedBox(height: 24),
            const Text(
              'حدث خطأ غير متوقع',
              style: TextStyle(
                color: AppColors.textLight,
                fontSize: 20,
                fontWeight: FontWeight.bold,
                fontFamily: 'Tajawal',
              ),
              textDirection: TextDirection.rtl,
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.darkSurface,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.error.withOpacity(0.3)),
              ),
              child: Text(
                details.exceptionAsString(),
                style: const TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 12,
                  fontFamily: 'Courier',
                ),
                textAlign: TextAlign.center,
                maxLines: 4,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
