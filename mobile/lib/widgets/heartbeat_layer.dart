import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../state/ui/tension_notifier.dart';
import '../core/theme/colors.dart';

/// Visual heartbeat pulse overlay for high tension moments.
class HeartbeatLayer extends ConsumerStatefulWidget {
  const HeartbeatLayer({super.key});

  @override
  ConsumerState<HeartbeatLayer> createState() => _HeartbeatLayerState();
}

class _HeartbeatLayerState extends ConsumerState<HeartbeatLayer>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    );

    _animation = CurvedAnimation(parent: _controller, curve: Curves.easeInOut);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tension = ref.watch(tensionProvider);

    // Hide if low tension
    if (tension.level < 0.3) {
      if (_controller.isAnimating) {
        _controller.stop();
        _controller.reset();
      }
      return const SizedBox.shrink();
    }

    // Update duration if BPM changed significantly
    final durationMs = (60000 / tension.bpm).round();
    if (_controller.duration?.inMilliseconds != durationMs) {
      _controller.duration = Duration(milliseconds: durationMs);
      if (_controller.isAnimating) {
        _controller.repeat(reverse: true);
      }
    }

    // Ensure animating
    if (!_controller.isAnimating) {
      _controller.repeat(reverse: true);
    }

    return IgnorePointer(
      child: AnimatedBuilder(
        animation: _animation,
        builder: (context, child) {
          // Opacity pulses between 0 and (level * 0.6)
          final maxOpacity = (tension.level * 0.6).clamp(0.0, 0.8);
          final opacity = _animation.value * maxOpacity;

          return Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: Alignment.center,
                radius: 1.2,
                colors: [
                  Colors.transparent,
                  AppColors.error.withOpacity(opacity),
                ],
                stops: const [0.6, 1.0],
              ),
            ),
          );
        },
      ),
    );
  }
}
