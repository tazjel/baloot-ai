import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';
import 'widgets/error_boundary_widget.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  ErrorBoundaryWidget.initialize();
  runApp(
    const ProviderScope(
      child: BalootApp(),
    ),
  );
}
