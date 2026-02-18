import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/widgets/game_toast_widget.dart';
import 'package:baloot_ai/state/ui/toast_notifier.dart';

void main() {
  group('GameToastWidget', () {
    testWidgets('renders with info toast', (tester) async {
      final toast = ToastMessage(id: '1', message: 'مرحبا', type: ToastType.info);
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: GameToastWidget(toast: toast, onDismiss: () {})),
      ));
      expect(find.text('مرحبا'), findsOneWidget);
    });

    testWidgets('has Semantics with liveRegion', (tester) async {
      final toast = ToastMessage(id: '2', message: 'دورك!', type: ToastType.turn);
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: GameToastWidget(toast: toast, onDismiss: () {})),
      ));

      final semanticsFinder = find.descendant(
        of: find.byType(GameToastWidget),
        matching: find.byType(Semantics),
      );
      final semanticsWidget = tester.widget<Semantics>(semanticsFinder.first);
      expect(semanticsWidget.properties.label, 'دورك!');
      expect(semanticsWidget.properties.liveRegion, isTrue);
    });

    testWidgets('wraps content in Dismissible', (tester) async {
      final toast = ToastMessage(id: '3', message: 'test', type: ToastType.info);
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: GameToastWidget(toast: toast, onDismiss: () {})),
      ));
      expect(find.byType(Dismissible), findsOneWidget);
    });

    testWidgets('renders different toast types', (tester) async {
      for (final type in [ToastType.error, ToastType.success, ToastType.warning, ToastType.trick]) {
        final toast = ToastMessage(id: type.name, message: 'msg', type: type);
        await tester.pumpWidget(MaterialApp(
          home: Scaffold(body: GameToastWidget(toast: toast, onDismiss: () {})),
        ));
        expect(find.byType(GameToastWidget), findsOneWidget);
      }
    });
  });
}
