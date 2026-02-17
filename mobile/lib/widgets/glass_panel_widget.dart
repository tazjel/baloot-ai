import 'package:flutter/material.dart';
import 'dart:ui';
import '../core/theme/colors.dart';

/// Frosted glass effect panel.
class GlassPanelWidget extends StatelessWidget {
  final Widget child;
  final double borderRadius;
  final double opacity;
  final Color tint;

  const GlassPanelWidget({
    super.key,
    required this.child,
    this.borderRadius = 16.0,
    this.opacity = 0.2,
    this.tint = AppColors.darkSurface,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          color: tint.withOpacity(opacity),
          child: child,
        ),
      ),
    );
  }
}
