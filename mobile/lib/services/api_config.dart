/// API Configuration — base URLs and environment.
class ApiConfig {
  static const String defaultUrl = 'http://localhost:3005';

  /// Get API base URL from environment or use default.
  static String get baseUrl {
    return const String.fromEnvironment('API_URL', defaultValue: defaultUrl);
  }

  /// WebSocket URL (same host as API).
  static String get socketUrl => baseUrl;
}
