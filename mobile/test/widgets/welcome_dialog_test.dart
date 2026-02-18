import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/widgets/welcome_dialog.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('WelcomeDialog shows 3 tutorial pages with correct titles and navigation',
      (WidgetTester tester) async {
    // Mock initial preferences
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) {
            return Scaffold(
              body: Center(
                child: ElevatedButton(
                  onPressed: () => showWelcomeIfFirstLaunch(context),
                  child: const Text('Show Dialog'),
                ),
              ),
            );
          },
        ),
      ),
    );

    // Tap to show dialog
    await tester.tap(find.text('Show Dialog'));
    await tester.pumpAndSettle();

    // Verify first page content
    expect(find.text('مرحباً ببلوت AI!'), findsOneWidget);
    expect(find.textContaining('لعبة البلوت السعودية'), findsOneWidget);

    // Verify first page buttons
    expect(find.text('التالي'), findsOneWidget);
    expect(find.text('السابق'), findsNothing);

    // Verify dots: 1 active (width 24), 2 inactive (width 8)
    expect(
      find.byWidgetPredicate(
        (w) => w is Container && w.constraints?.minWidth == 24.0,
      ),
      findsOneWidget,
    );
    expect(
      find.byWidgetPredicate(
        (w) => w is Container && w.constraints?.minWidth == 8.0,
      ),
      findsNWidgets(2),
    );

    // Tap 'التالي' to go to second page
    await tester.tap(find.text('التالي'));
    await tester.pumpAndSettle();

    // Verify second page content
    expect(find.text('4 مستويات ذكاء'), findsOneWidget);

    // Verify second page buttons
    expect(find.text('التالي'), findsOneWidget);
    expect(find.text('السابق'), findsOneWidget);

    // Tap 'التالي' to go to third page
    await tester.tap(find.text('التالي'));
    await tester.pumpAndSettle();

    // Verify third page content
    expect(find.text('كيف تلعب'), findsOneWidget);

    // Verify third page buttons (Last page)
    expect(find.text('ابدأ اللعب!'), findsOneWidget);
    expect(find.text('السابق'), findsOneWidget);

    // Tap 'السابق' to go back to second page
    await tester.tap(find.text('السابق'));
    await tester.pumpAndSettle();

    // Verify we are back on second page
    expect(find.text('4 مستويات ذكاء'), findsOneWidget);
    expect(find.text('ابدأ اللعب!'), findsNothing);
    expect(find.text('التالي'), findsOneWidget);
  });
}
