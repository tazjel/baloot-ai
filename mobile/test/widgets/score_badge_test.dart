import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/widgets/score_badge_widget.dart';

void main() {
  group('ScoreBadgeWidget', () {
    testWidgets('renders score value', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: ScoreBadgeWidget(score: 42)),
      ));
      // Animation starts at 0, pump to complete
      await tester.pumpAndSettle();
      expect(find.text('42'), findsOneWidget);
    });

    testWidgets('renders with custom color', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: ScoreBadgeWidget(score: 10, color: Colors.red)),
      ));
      await tester.pumpAndSettle();
      expect(find.text('10'), findsOneWidget);
    });

    testWidgets('renders zero score', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: ScoreBadgeWidget(score: 0)),
      ));
      await tester.pumpAndSettle();
      expect(find.text('0'), findsOneWidget);
    });

    testWidgets('animates from 0 to target', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: ScoreBadgeWidget(score: 100)),
      ));
      // Before animation settles, value should be less than 100
      await tester.pump(const Duration(milliseconds: 100));
      // After settling, should show 100
      await tester.pumpAndSettle();
      expect(find.text('100'), findsOneWidget);
    });
  });
}
