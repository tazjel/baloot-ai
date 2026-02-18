/// Generates the app icon as a 1024x1024 PNG.
///
/// Run: dart run tool/generate_icon.dart
/// Output: assets/images/app_icon.png
///
/// Design: Gold spade symbol on dark green-black gradient background
/// with subtle gold border ring.
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

Future<void> main() async {
  const size = 1024;
  final recorder = ui.PictureRecorder();
  final canvas = ui.Canvas(recorder);
  final rect = ui.Rect.fromLTWH(0, 0, size.toDouble(), size.toDouble());

  // Background — dark gradient
  final bgPaint = ui.Paint()
    ..shader = ui.Gradient.radial(
      ui.Offset(size / 2, size / 2),
      size * 0.7,
      [
        const ui.Color(0xFF1a2332), // Dark blue-gray center
        const ui.Color(0xFF0d1117), // Near-black edge
      ],
    );
  canvas.drawRect(rect, bgPaint);

  // Rounded corners mask — draw rounded rect
  final rrect = ui.RRect.fromRectAndRadius(
    rect,
    const ui.Radius.circular(size * 0.22),
  );
  canvas.clipRRect(rrect);
  canvas.drawRect(rect, bgPaint);

  // Subtle inner border ring
  final borderPaint = ui.Paint()
    ..color = const ui.Color(0x40D4AF37) // Gold at 25% opacity
    ..style = ui.PaintingStyle.stroke
    ..strokeWidth = size * 0.02;
  final borderRRect = ui.RRect.fromRectAndRadius(
    ui.Rect.fromLTWH(
      size * 0.04, size * 0.04,
      size * 0.92, size * 0.92,
    ),
    const ui.Radius.circular(size * 0.18),
  );
  canvas.drawRRect(borderRRect, borderPaint);

  // Spade symbol — using path
  final spadePath = _createSpadePath(size.toDouble());

  // Spade glow
  final glowPaint = ui.Paint()
    ..color = const ui.Color(0x30D4AF37)
    ..maskFilter = const ui.MaskFilter.blur(ui.BlurStyle.normal, 30);
  canvas.drawPath(spadePath, glowPaint);

  // Spade fill — gold gradient
  final spadePaint = ui.Paint()
    ..shader = ui.Gradient.linear(
      ui.Offset(size / 2, size * 0.2),
      ui.Offset(size / 2, size * 0.75),
      [
        const ui.Color(0xFFFFD700), // Bright gold top
        const ui.Color(0xFFD4AF37), // Rich gold middle
        const ui.Color(0xFFB8860B), // Dark gold bottom
      ],
      [0.0, 0.5, 1.0],
    );
  canvas.drawPath(spadePath, spadePaint);

  // "AI" text at bottom
  final textParagraphBuilder = ui.ParagraphBuilder(
    ui.ParagraphStyle(
      textAlign: ui.TextAlign.center,
      fontSize: size * 0.12,
      fontWeight: ui.FontWeight.bold,
    ),
  )
    ..pushStyle(ui.TextStyle(
      color: const ui.Color(0xAAD4AF37),
      fontSize: size * 0.12,
      fontWeight: ui.FontWeight.bold,
      letterSpacing: size * 0.03,
    ))
    ..addText('AI');
  final textParagraph = textParagraphBuilder.build()
    ..layout(ui.ParagraphConstraints(width: size.toDouble()));
  canvas.drawParagraph(
    textParagraph,
    ui.Offset(0, size * 0.78),
  );

  // Render
  final picture = recorder.endRecording();
  final image = await picture.toImage(size, size);
  final byteData = await image.toByteData(format: ui.ImageByteFormat.png);

  if (byteData == null) {
    print('Failed to encode image');
    exit(1);
  }

  final outputDir = Directory('assets/images');
  if (!outputDir.existsSync()) {
    outputDir.createSync(recursive: true);
  }

  final file = File('assets/images/app_icon.png');
  await file.writeAsBytes(byteData.buffer.asUint8List());
  print('Icon generated: ${file.path} (${byteData.lengthInBytes} bytes)');
}

/// Creates a spade shape path centered in the canvas.
ui.Path _createSpadePath(double size) {
  final path = ui.Path();
  final cx = size / 2;
  final scale = size / 1024;

  // Spade body — built from curves
  // Start at the tip (bottom of the spade bulb, top of the stem)
  path.moveTo(cx, size * 0.18); // Top point

  // Right curve of spade
  path.cubicTo(
    cx + 80 * scale, size * 0.22,   // CP1
    cx + 260 * scale, size * 0.32,  // CP2
    cx + 240 * scale, size * 0.50,  // End — right bulge
  );
  path.cubicTo(
    cx + 220 * scale, size * 0.66,  // CP1
    cx + 60 * scale, size * 0.62,   // CP2
    cx + 30 * scale, size * 0.68,   // End — near center bottom
  );

  // Stem right curve
  path.quadraticBezierTo(
    cx + 80 * scale, size * 0.72,
    cx + 60 * scale, size * 0.78,
  );

  // Stem bottom
  path.lineTo(cx - 60 * scale, size * 0.78);

  // Stem left curve
  path.quadraticBezierTo(
    cx - 80 * scale, size * 0.72,
    cx - 30 * scale, size * 0.68,
  );

  // Left curve of spade
  path.cubicTo(
    cx - 60 * scale, size * 0.62,   // CP1
    cx - 220 * scale, size * 0.66,  // CP2
    cx - 240 * scale, size * 0.50,  // End — left bulge
  );
  path.cubicTo(
    cx - 260 * scale, size * 0.32,  // CP1
    cx - 80 * scale, size * 0.22,   // CP2
    cx, size * 0.18,                // Back to top point
  );

  path.close();
  return path;
}
