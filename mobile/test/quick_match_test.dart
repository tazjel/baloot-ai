/// Tests for M-MP7: Quick Match UI — screen rendering and state.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:baloot_ai/screens/quick_match_screen.dart';

void main() {
  group('QuickMatchScreen', () {
    testWidgets('renders initial search button', (tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(home: QuickMatchScreen()),
        ),
      );
      await tester.pump();

      // Should show the start view with search button
      expect(find.text('مباراة سريعة'), findsOneWidget); // AppBar title
      expect(find.text('ابحث عن مباراة'), findsOneWidget); // Button
      expect(find.text('العب مباراة مصنفة'), findsOneWidget); // Subtitle
    });

    testWidgets('shows description text', (tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(home: QuickMatchScreen()),
        ),
      );
      await tester.pump();

      expect(
        find.text('سيتم مطابقتك مع لاعبين بنفس مستواك'),
        findsOneWidget,
      );
    });

    testWidgets('has game controller icon', (tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(home: QuickMatchScreen()),
        ),
      );
      await tester.pump();

      expect(find.byIcon(Icons.sports_esports), findsOneWidget);
    });

    testWidgets('has back button', (tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(home: QuickMatchScreen()),
        ),
      );
      await tester.pump();

      expect(find.byIcon(Icons.arrow_back), findsOneWidget);
    });
  });
}
