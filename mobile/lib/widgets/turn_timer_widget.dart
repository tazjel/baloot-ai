import 'package:flutter/material.dart';
import '../core/theme/colors.dart';

/// Circular timer indicating remaining turn time.
class TurnTimerWidget extends StatelessWidget {
  final double value; // 0.0 to 1.0
  final double size;

  const TurnTimerWidget({
    super.key,
    required this.value,
    this.size = 24,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        value: value,
        strokeWidth: 3,
        backgroundColor: AppColors.darkSurface.withOpacity(0.3),
        valueColor: AlwaysStoppedAnimation<Color>(_getColor(value)),
      ),
    );
  }

  Color _getColor(double value) {
    if (value > 0.5) return AppColors.success;
    if (value > 0.3) return AppColors.warning;
    return AppColors.error;
  }
}
