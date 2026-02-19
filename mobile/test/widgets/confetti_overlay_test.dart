import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/widgets/confetti_overlay.dart';

void main() {
  group('ConfettiOverlay', () {
    testWidgets('renders without error', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: ConfettiOverlay()),
      ));
      expect(find.byType(ConfettiOverlay), findsOneWidget);
    });

    testWidgets('uses IgnorePointer to not block interaction', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: ConfettiOverlay()),
      ));
      expect(
        find.descendant(
          of: find.byType(ConfettiOverlay),
          matching: find.byType(IgnorePointer),
        ),
        findsOneWidget,
      );
    });

    testWidgets('contains CustomPaint for particle rendering', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: ConfettiOverlay()),
      ));
      expect(
        find.descendant(
          of: find.byType(ConfettiOverlay),
          matching: find.byType(CustomPaint),
        ),
        findsOneWidget,
      );
    });

    testWidgets('accepts custom duration', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: ConfettiOverlay(duration: Duration(seconds: 2))),
      ));
      expect(find.byType(ConfettiOverlay), findsOneWidget);
    });

    testWidgets('accepts custom particle count', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: ConfettiOverlay(particleCount: 25)),
      ));
      expect(find.byType(ConfettiOverlay), findsOneWidget);
    });
  });
}
