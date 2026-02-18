/// confetti_overlay.dart — Celebratory confetti animation for wins.
///
/// Lightweight particle system with falling gold/colored rectangles.
/// Used as an overlay on the game over dialog when the player wins.
library;
import 'dart:math';

import 'package:flutter/material.dart';

/// A full-screen confetti animation overlay.
///
/// Spawns gold/colored particles that fall and rotate.
/// Automatically plays for [duration] then fades out.
class ConfettiOverlay extends StatefulWidget {
  /// How long the confetti plays before fading.
  final Duration duration;

  /// Number of confetti particles.
  final int particleCount;

  const ConfettiOverlay({
    super.key,
    this.duration = const Duration(seconds: 4),
    this.particleCount = 50,
  });

  @override
  State<ConfettiOverlay> createState() => _ConfettiOverlayState();
}

class _ConfettiOverlayState extends State<ConfettiOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final List<_Particle> _particles;
  final _random = Random();

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: widget.duration,
    );

    _particles = List.generate(widget.particleCount, (_) => _Particle(_random));
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          final opacity = _controller.value > 0.8
              ? (1.0 - _controller.value) / 0.2
              : 1.0;
          return Opacity(
            opacity: opacity.clamp(0.0, 1.0),
            child: CustomPaint(
              painter: _ConfettiPainter(
                particles: _particles,
                progress: _controller.value,
              ),
              size: Size.infinite,
            ),
          );
        },
      ),
    );
  }
}

class _Particle {
  final double x; // 0-1 horizontal position
  final double startY; // -0.2 to -0.1 start above screen
  final double speed; // fall speed multiplier
  final double size; // particle size
  final double rotation; // initial rotation
  final double rotationSpeed; // rotation speed
  final double drift; // horizontal drift
  final Color color;

  _Particle(Random r)
      : x = r.nextDouble(),
        startY = -0.1 - r.nextDouble() * 0.3,
        speed = 0.5 + r.nextDouble() * 0.8,
        size = 4 + r.nextDouble() * 6,
        rotation = r.nextDouble() * 2 * pi,
        rotationSpeed = (r.nextDouble() - 0.5) * 6,
        drift = (r.nextDouble() - 0.5) * 0.15,
        color = _randomColor(r);

  static Color _randomColor(Random r) {
    const colors = [
      Color(0xFFD4AF37), // Gold
      Color(0xFFF4D03F), // Light gold
      Color(0xFFB8860B), // Dark gold
      Color(0xFFFFD700), // Bright gold
      Color(0xFF3B82F6), // Blue
      Color(0xFF22C55E), // Green
      Color(0xFFEF4444), // Red
      Color(0xFFF59E0B), // Amber
    ];
    return colors[r.nextInt(colors.length)];
  }
}

class _ConfettiPainter extends CustomPainter {
  final List<_Particle> particles;
  final double progress;

  _ConfettiPainter({required this.particles, required this.progress});

  @override
  void paint(Canvas canvas, Size size) {
    for (final p in particles) {
      final x = (p.x + p.drift * progress) * size.width;
      final y = (p.startY + progress * p.speed * 1.3) * size.height;

      if (y > size.height || y < -20) continue;

      final paint = Paint()..color = p.color;
      canvas.save();
      canvas.translate(x, y);
      canvas.rotate(p.rotation + p.rotationSpeed * progress);
      canvas.drawRect(
        Rect.fromCenter(center: Offset.zero, width: p.size, height: p.size * 0.6),
        paint,
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_ConfettiPainter oldDelegate) =>
      oldDelegate.progress != progress;
}
