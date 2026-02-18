// test_driver/main.dart — Flutter Driver entrypoint.
//
// Launches the app with the Flutter Driver extension enabled,
// allowing automated UI interaction via flutter_driver commands.
//
// Usage:
//   flutter run --target=test_driver/main.dart -d chrome
//
// Or via MCP:
//   mcp_dart_launch_app(target: "test_driver/main.dart")
import 'package:flutter_driver/driver_extension.dart';
import 'package:baloot_ai/main.dart' as app;

void main() {
  enableFlutterDriverExtension();
  app.main();
}
