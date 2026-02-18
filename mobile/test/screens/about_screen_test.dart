import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/screens/about_screen.dart';

void main() {
  testWidgets('AboutScreen shows all required content', (WidgetTester tester) async {
    // Pump the widget
    await tester.pumpWidget(const MaterialApp(home: AboutScreen()));

    // Verify headers and titles
    expect(find.text('حول التطبيق'), findsOneWidget);
    expect(find.text('بلوت AI'), findsOneWidget);
    expect(find.text('الإصدار 1.0.0'), findsOneWidget);

    // Verify section headers
    expect(find.text('المميزات'), findsOneWidget);
    expect(find.text('التقنيات'), findsOneWidget);
    expect(find.text('قواعد اللعبة'), findsOneWidget);
    expect(find.text('عن اللعبة'), findsOneWidget);

    // Verify footer
    // We might need to scroll to see the footer if the screen is small
    // Default test screen size is 800x600, which might be enough or not.
    // Let's try to find it first.
    final footerFinder = find.text('صُنع بـ ❤️ في السعودية');

    // If not found, scroll down
    if (tester.widgetList(footerFinder).isEmpty) {
       await tester.drag(find.byType(SingleChildScrollView), const Offset(0, -500));
       await tester.pumpAndSettle();
    }

    expect(footerFinder, findsOneWidget);
    expect(find.text('© 2026 Baloot AI'), findsOneWidget);
  });
}
