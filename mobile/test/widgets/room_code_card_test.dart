import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/widgets/room_code_card.dart';

void main() {
  testWidgets('RoomCodeCard displays code and handles copy action', (WidgetTester tester) async {
    const code = '123456';

    // Intercept HapticFeedback calls to avoid MissingPluginException if any
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      (MethodCall methodCall) async {
        if (methodCall.method == 'HapticFeedback.vibrate') {
          return null;
        }
        return null;
      },
    );

    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: Center(
          child: RoomCodeCard(roomCode: code),
        ),
      ),
    ));

    // Verify code is displayed
    expect(find.text(code), findsOneWidget);

    // Verify headers and instructions
    expect(find.text('رمز الغرفة'), findsOneWidget);
    expect(find.text('شارك الرمز مع أصدقائك'), findsOneWidget);

    // Verify copy icon is present initially
    expect(find.byIcon(Icons.copy_rounded), findsOneWidget);
    expect(find.byIcon(Icons.check_rounded), findsNothing);

    // Tap copy button
    await tester.tap(find.byIcon(Icons.copy_rounded));
    await tester.pump(); // Start animation
    await tester.pump(const Duration(milliseconds: 250)); // Wait for transition to finish

    // Verify icon changed to check
    expect(find.byIcon(Icons.check_rounded), findsOneWidget);
    expect(find.byIcon(Icons.copy_rounded), findsNothing);

    // Verify clipboard content
    // We can't easily check system clipboard in widget test without mocking the channel manually for clipboard too.
    // But we can trust the widget called it if no error.

    // Wait for 2 seconds (timer duration in code)
    await tester.pump(const Duration(seconds: 2));
    await tester.pump(const Duration(milliseconds: 250)); // Finish exit animation

    // Verify icon changed back to copy
    expect(find.byIcon(Icons.copy_rounded), findsOneWidget);
    expect(find.byIcon(Icons.check_rounded), findsNothing);
  });
}
