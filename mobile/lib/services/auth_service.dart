/// auth_service.dart — HTTP client for authentication endpoints.
///
/// Calls the Python backend's /signup, /signin, and /user endpoints.
/// Returns typed results; does not manage state (that's AuthNotifier's job).
library;

import 'dart:convert';
import 'dart:developer' as dev;
import 'package:http/http.dart' as http;

import 'api_config.dart';

/// Result of an auth operation (signup or signin).
class AuthResult {
  final bool success;
  final String? token;
  final String? email;
  final String? firstName;
  final String? lastName;
  final int? leaguePoints;
  final String? tier;
  final String? error;

  const AuthResult({
    required this.success,
    this.token,
    this.email,
    this.firstName,
    this.lastName,
    this.leaguePoints,
    this.tier,
    this.error,
  });
}

/// HTTP client for the backend auth API.
class AuthService {
  AuthService._();

  static final _log = 'AUTH_SERVICE';

  /// Sign up a new user. Returns AuthResult with user info (no token yet).
  static Future<AuthResult> signUp({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
  }) async {
    try {
      final url = Uri.parse('${ApiConfig.baseUrl}/signup');
      final resp = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'firstName': firstName,
          'lastName': lastName,
          'email': email,
          'password': password,
        }),
      );

      final data = jsonDecode(resp.body) as Map<String, dynamic>;

      if (resp.statusCode == 201) {
        dev.log('Signup success: $email', name: _log);
        return AuthResult(
          success: true,
          email: data['email'] as String?,
          firstName: data['firstName'] as String?,
          lastName: data['lastName'] as String?,
        );
      }

      dev.log('Signup failed: ${data['error']}', name: _log);
      return AuthResult(
        success: false,
        error: data['error'] as String? ?? 'فشل التسجيل',
      );
    } catch (e) {
      dev.log('Signup error: $e', name: _log);
      return AuthResult(
        success: false,
        error: 'خطأ في الاتصال بالخادم',
      );
    }
  }

  /// Sign in an existing user. Returns AuthResult with JWT token.
  static Future<AuthResult> signIn({
    required String email,
    required String password,
  }) async {
    try {
      final url = Uri.parse('${ApiConfig.baseUrl}/signin');
      final resp = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'password': password,
        }),
      );

      final data = jsonDecode(resp.body) as Map<String, dynamic>;

      if (resp.statusCode == 200 && data.containsKey('token')) {
        dev.log('Signin success: $email', name: _log);
        return AuthResult(
          success: true,
          token: data['token'] as String?,
          email: data['email'] as String?,
          firstName: data['firstName'] as String?,
          lastName: data['lastName'] as String?,
        );
      }

      dev.log('Signin failed: ${data['error']}', name: _log);
      return AuthResult(
        success: false,
        error: data['error'] as String? ?? 'فشل تسجيل الدخول',
      );
    } catch (e) {
      dev.log('Signin error: $e', name: _log);
      return AuthResult(
        success: false,
        error: 'خطأ في الاتصال بالخادم',
      );
    }
  }

  /// Refresh a JWT token before it expires.
  ///
  /// Calls POST /auth/refresh with the current token. Returns a new token
  /// with fresh 24h expiry, or an error if the token is already expired.
  static Future<AuthResult> refreshToken(String token) async {
    try {
      final url = Uri.parse('${ApiConfig.baseUrl}/auth/refresh');
      final resp = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final newToken = data['token'] as String?;
        if (newToken != null) {
          dev.log('Token refreshed successfully', name: _log);
          return AuthResult(success: true, token: newToken);
        }
      }

      if (resp.statusCode == 429) {
        dev.log('Refresh rate limited', name: _log);
        return const AuthResult(
          success: false,
          error: 'طلبات كثيرة، حاول لاحقاً',
        );
      }

      dev.log('Refresh failed: ${resp.statusCode}', name: _log);
      return const AuthResult(success: false, error: 'فشل تجديد الجلسة');
    } catch (e) {
      dev.log('Refresh error: $e', name: _log);
      return const AuthResult(
        success: false,
        error: 'خطأ في الاتصال بالخادم',
      );
    }
  }

  /// Validate a stored token by calling GET /user.
  /// Returns AuthResult with user profile if token is valid.
  static Future<AuthResult> validateToken(String token) async {
    try {
      final url = Uri.parse('${ApiConfig.baseUrl}/user');
      final resp = await http.get(
        url,
        headers: {'Authorization': 'Bearer $token'},
      );

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final user = data['user'] as Map<String, dynamic>?;
        dev.log('Token valid', name: _log);
        return AuthResult(
          success: true,
          token: token,
          email: user?['email'] as String?,
          firstName: user?['first_name'] as String?,
          lastName: user?['last_name'] as String?,
          leaguePoints: data['leaguePoints'] as int?,
          tier: data['tier'] as String?,
        );
      }

      dev.log('Token invalid: ${resp.statusCode}', name: _log);
      return const AuthResult(success: false, error: 'انتهت صلاحية الجلسة');
    } catch (e) {
      dev.log('Token validation error: $e', name: _log);
      return const AuthResult(success: false, error: 'خطأ في الاتصال بالخادم');
    }
  }
}
