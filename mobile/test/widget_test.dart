import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baloot_ai/screens/login_screen.dart';

void main() {
  testWidgets('LoginScreen renders sign-in form', (WidgetTester tester) async {
    // Test the login screen directly. The full BalootApp now starts with
    // auth flow (M-MP3): splash → login (guest) or splash → lobby.
    // SplashScreen has pending timers from _initAndNavigate, so we test
    // the login form in isolation instead.
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: const LoginScreen(),
          // GoRouter stubs not needed — LoginScreen only uses context.go
          // on user actions, not on build.
        ),
      ),
    );
    await tester.pump();

    // Login screen shows Arabic branding and form elements
    expect(find.text('بلوت AI'), findsOneWidget);
    expect(find.text('تسجيل الدخول'), findsOneWidget); // "Sign In" header
    expect(find.text('دخول'), findsOneWidget); // Sign-in button
    expect(find.text('تابع كضيف'), findsOneWidget); // "Continue as guest"
  });
}
