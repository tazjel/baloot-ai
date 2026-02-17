import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baloot_ai/app.dart';

void main() {
  testWidgets('App launches and shows lobby', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: BalootApp()),
    );
    await tester.pumpAndSettle();

    // Verify the lobby screen shows
    expect(find.text('بلوت AI'), findsOneWidget);
    expect(find.text('ابدأ اللعبة'), findsOneWidget);
  });
}
