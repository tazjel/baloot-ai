/// API Configuration — base URLs and environment variables.
///
/// Provides the base URL for the Python FastAPI backend and Socket.IO
/// WebSocket connection. The URL can be overridden at build time via
/// `--dart-define=API_URL=https://your-server.com`.
///
/// Default: `http://localhost:3005` (local development server).
class ApiConfig {
  /// Default API URL for local development.
  static const String defaultUrl = 'http://localhost:3005';

  /// Returns the API base URL, reading from the `API_URL` environment
  /// variable set via `--dart-define`. Falls back to [defaultUrl].
  static String get baseUrl {
    return const String.fromEnvironment('API_URL', defaultValue: defaultUrl);
  }

  /// WebSocket URL for Socket.IO connection.
  ///
  /// Uses the same host as the REST API. The `socket_io_client` package
  /// will append `/socket.io/` path automatically.
  static String get socketUrl => baseUrl;
}
