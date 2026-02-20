/// auth_notifier.dart — Authentication state management with Riverpod.
///
/// Manages JWT token persistence, user profile, and auth lifecycle.
/// Token is stored in SharedPreferences and validated on app start.
library;

import 'dart:developer' as dev;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/auth_service.dart';

/// SharedPreferences key for the JWT token.
const _kTokenKey = 'baloot_auth_token';

/// Authentication state.
class AuthState {
  /// JWT token (null if not authenticated).
  final String? token;

  /// User email.
  final String? email;

  /// User first name.
  final String? firstName;

  /// User last name.
  final String? lastName;

  /// League points (from server profile).
  final int? leaguePoints;

  /// Tier name (Bronze, Silver, etc.).
  final String? tier;

  /// Whether an auth operation is in progress.
  final bool isLoading;

  /// Error message from the last failed operation.
  final String? error;

  /// Whether the initial token check has completed.
  final bool initialized;

  const AuthState({
    this.token,
    this.email,
    this.firstName,
    this.lastName,
    this.leaguePoints,
    this.tier,
    this.isLoading = false,
    this.error,
    this.initialized = false,
  });

  /// Whether the user is authenticated (has a token).
  bool get isAuthenticated => token != null;

  /// Display name: first name, or email prefix, or 'ضيف'.
  String get displayName {
    if (firstName != null && firstName!.isNotEmpty) return firstName!;
    if (email != null && email!.isNotEmpty) {
      return email!.split('@').first;
    }
    return 'ضيف';
  }

  AuthState copyWith({
    String? token,
    String? email,
    String? firstName,
    String? lastName,
    int? leaguePoints,
    String? tier,
    bool? isLoading,
    String? error,
    bool? initialized,
    bool clearToken = false,
    bool clearError = false,
  }) {
    return AuthState(
      token: clearToken ? null : (token ?? this.token),
      email: clearToken ? null : (email ?? this.email),
      firstName: clearToken ? null : (firstName ?? this.firstName),
      lastName: clearToken ? null : (lastName ?? this.lastName),
      leaguePoints: clearToken ? null : (leaguePoints ?? this.leaguePoints),
      tier: clearToken ? null : (tier ?? this.tier),
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      initialized: initialized ?? this.initialized,
    );
  }
}

/// Manages authentication state, token persistence, and API calls.
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState());

  /// Initialize: load stored token and validate it.
  ///
  /// Called once on app start from SplashScreen.
  /// Sets [AuthState.initialized] to true when done.
  Future<void> initialize() async {
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      final prefs = await SharedPreferences.getInstance();
      final storedToken = prefs.getString(_kTokenKey);

      if (storedToken == null) {
        dev.log('No stored token', name: 'AUTH');
        state = state.copyWith(isLoading: false, initialized: true);
        return;
      }

      // Validate the stored token with the server
      final result = await AuthService.validateToken(storedToken);

      if (result.success) {
        state = state.copyWith(
          token: result.token,
          email: result.email,
          firstName: result.firstName,
          lastName: result.lastName,
          leaguePoints: result.leaguePoints,
          tier: result.tier,
          isLoading: false,
          initialized: true,
        );
        dev.log('Token restored: ${result.email}', name: 'AUTH');
      } else {
        // Token expired or invalid — clear it
        await prefs.remove(_kTokenKey);
        state = state.copyWith(
          isLoading: false,
          initialized: true,
          clearToken: true,
        );
        dev.log('Stored token invalid, cleared', name: 'AUTH');
      }
    } catch (e) {
      dev.log('Init error: $e', name: 'AUTH');
      // On network error, still mark as initialized but don't clear token
      // (user might be offline — we'll let them proceed as guest)
      state = state.copyWith(isLoading: false, initialized: true);
    }
  }

  /// Sign up a new account, then automatically sign in.
  Future<bool> signUp({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);

    final signUpResult = await AuthService.signUp(
      firstName: firstName,
      lastName: lastName,
      email: email,
      password: password,
    );

    if (!signUpResult.success) {
      state = state.copyWith(isLoading: false, error: signUpResult.error);
      return false;
    }

    // Auto sign-in after successful signup
    return signIn(email: email, password: password);
  }

  /// Sign in with email and password.
  Future<bool> signIn({
    required String email,
    required String password,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);

    final result = await AuthService.signIn(email: email, password: password);

    if (result.success && result.token != null) {
      // Persist token
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_kTokenKey, result.token!);

      // Also save player name for multiplayer screen
      await prefs.setString('baloot_player_name', result.firstName ?? '');

      state = state.copyWith(
        token: result.token,
        email: result.email,
        firstName: result.firstName,
        lastName: result.lastName,
        isLoading: false,
      );
      dev.log('Signed in: ${result.email}', name: 'AUTH');
      return true;
    }

    state = state.copyWith(isLoading: false, error: result.error);
    return false;
  }

  /// Refresh the current JWT token before it expires.
  ///
  /// Call this proactively (e.g., on app resume, before matchmaking)
  /// or reactively when the server returns 401.
  /// Returns true if a new token was obtained and persisted.
  Future<bool> refreshToken() async {
    final currentToken = state.token;
    if (currentToken == null) {
      dev.log('Cannot refresh: no token', name: 'AUTH');
      return false;
    }

    final result = await AuthService.refreshToken(currentToken);

    if (result.success && result.token != null) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_kTokenKey, result.token!);
      state = state.copyWith(token: result.token);
      dev.log('Token refreshed', name: 'AUTH');
      return true;
    }

    // If refresh fails because token is expired, sign out
    if (!result.success) {
      dev.log('Token refresh failed: ${result.error}', name: 'AUTH');
    }
    return false;
  }

  /// Continue as guest (no account, local-only stats).
  void continueAsGuest() {
    state = state.copyWith(
      initialized: true,
      isLoading: false,
      clearToken: true,
      clearError: true,
    );
    dev.log('Continuing as guest', name: 'AUTH');
  }

  /// Sign out: clear token and state.
  Future<void> signOut() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_kTokenKey);
    } catch (_) {}

    state = const AuthState(initialized: true);
    dev.log('Signed out', name: 'AUTH');
  }

  /// Clear any error message.
  void clearError() {
    state = state.copyWith(clearError: true);
  }
}
