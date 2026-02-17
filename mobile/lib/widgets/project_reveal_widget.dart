import 'package:flutter/material.dart';
import '../core/theme/colors.dart';
import '../models/declared_project.dart';
import '../models/enums.dart';
import 'suit_icon_widget.dart';

/// Animated reveal card for declared projects (Sira, Baloot, etc).
class ProjectRevealWidget extends StatefulWidget {
  final DeclaredProject project;
  final String playerName;
  final VoidCallback? onDismiss;

  const ProjectRevealWidget({
    super.key,
    required this.project,
    required this.playerName,
    this.onDismiss,
  });

  @override
  State<ProjectRevealWidget> createState() => _ProjectRevealWidgetState();
}

class _ProjectRevealWidgetState extends State<ProjectRevealWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnim;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );

    _scaleAnim = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.elasticOut),
    );

    _fadeAnim = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: const Interval(0.0, 0.6, curve: Curves.easeIn)),
    );

    _controller.forward();

    if (widget.onDismiss != null) {
      Future.delayed(const Duration(seconds: 3), () {
        if (mounted) {
          _controller.reverse().then((_) => widget.onDismiss!());
        }
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: _scaleAnim,
      child: FadeTransition(
        opacity: _fadeAnim,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          decoration: BoxDecoration(
            color: AppColors.darkSurface.withOpacity(0.9),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.goldPrimary, width: 2),
            boxShadow: [
              BoxShadow(
                color: AppColors.goldPrimary.withOpacity(0.3),
                blurRadius: 20,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.star_rounded, color: AppColors.goldPrimary, size: 32),
              const SizedBox(height: 8),
              Text(
                _getProjectName(widget.project.type),
                style: const TextStyle(
                  color: AppColors.goldPrimary,
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  shadows: [
                    Shadow(color: Colors.black, blurRadius: 2, offset: Offset(1, 1)),
                  ],
                ),
              ),
              const SizedBox(height: 4),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    widget.playerName,
                    style: const TextStyle(color: AppColors.textMuted, fontSize: 16),
                  ),
                  const SizedBox(width: 8),
                  // Only show suit for sequences and Baloot
                  if (widget.project.type == ProjectType.sira ||
                      widget.project.type == ProjectType.fifty ||
                      widget.project.type == ProjectType.baloot)
                     SuitIconWidget(suit: widget.project.suit, size: 18),
                ],
              ),
              if (widget.project.score != null) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.goldPrimary.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '+${widget.project.score}',
                    style: const TextStyle(
                      color: AppColors.goldLight,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  String _getProjectName(ProjectType type) {
    switch (type) {
      case ProjectType.sira: return 'سرا';
      case ProjectType.fifty: return 'خمسين';
      case ProjectType.hundred: return 'مائة';
      case ProjectType.fourHundred: return 'أربعمائة';
      case ProjectType.baloot: return 'بلوت';
    }
  }
}
