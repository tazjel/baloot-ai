import 'package:flutter/material.dart';

/// Comic-style speech bubble with a pointer triangle.
class SpeechBubbleWidget extends StatelessWidget {
  final Widget child;
  final Color color;
  final double pointerHeight;
  final double pointerWidth;
  final EdgeInsets padding;
  final double borderRadius;

  const SpeechBubbleWidget({
    super.key,
    required this.child,
    this.color = Colors.white,
    this.pointerHeight = 10.0,
    this.pointerWidth = 16.0,
    this.padding = const EdgeInsets.all(12),
    this.borderRadius = 8.0,
  });

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _BubblePainter(
        color: color,
        pointerHeight: pointerHeight,
        pointerWidth: pointerWidth,
        radius: borderRadius,
      ),
      child: Container(
        padding: padding.copyWith(bottom: padding.bottom + pointerHeight),
        child: child,
      ),
    );
  }
}

class _BubblePainter extends CustomPainter {
  final Color color;
  final double pointerHeight;
  final double pointerWidth;
  final double radius;

  _BubblePainter({
    required this.color,
    required this.pointerHeight,
    required this.pointerWidth,
    required this.radius,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    final shadowPaint = Paint()
      ..color = Colors.black.withOpacity(0.15)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);

    final w = size.width;
    final h = size.height - pointerHeight;
    final r = radius;
    final cx = w / 2;
    final pw = pointerWidth / 2;

    final path = Path()
      ..moveTo(r, 0)
      ..lineTo(w - r, 0)
      ..arcToPoint(Offset(w, r), radius: Radius.circular(r))
      ..lineTo(w, h - r)
      ..arcToPoint(Offset(w - r, h), radius: Radius.circular(r))
      // Bottom side with pointer
      ..lineTo(cx + pw, h)
      ..lineTo(cx, size.height)
      ..lineTo(cx - pw, h)
      ..lineTo(r, h)
      ..arcToPoint(Offset(0, h - r), radius: Radius.circular(r))
      ..lineTo(0, r)
      ..arcToPoint(Offset(r, 0), radius: Radius.circular(r))
      ..close();

    canvas.drawPath(path, shadowPaint);
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(_BubblePainter oldDelegate) =>
      oldDelegate.color != color ||
      oldDelegate.pointerHeight != pointerHeight;
}
