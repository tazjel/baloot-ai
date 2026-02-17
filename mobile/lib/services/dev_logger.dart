import 'dart:developer' as developer;
import 'package:flutter/foundation.dart';

class DevLogger {
  static void info(String message) {
    if (kDebugMode) {
      developer.log('INFO: $message', name: 'BalootAI');
    }
  }

  static void warn(String message) {
    if (kDebugMode) {
      developer.log('WARN: $message', name: 'BalootAI', level: 900);
    }
  }

  static void error(String message, [StackTrace? stackTrace]) {
    if (kDebugMode) {
      developer.log(
        'ERROR: $message',
        name: 'BalootAI',
        error: message,
        stackTrace: stackTrace,
        level: 1000,
      );
    }
  }
}
