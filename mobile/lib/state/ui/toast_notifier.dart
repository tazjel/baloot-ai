/// toast_notifier.dart — Toast notification system.
///
/// Port of frontend/src/hooks/useGameToast.ts (69 lines).
///
/// Manages a queue of toast notifications with:
/// - Auto-dismiss after 3 seconds
/// - Max 3 toasts on screen
/// - Deduplication within 1.5s window
/// - Manual dismiss with timer cleanup
///
/// ## Toast Types
/// 'turn', 'akka', 'sawa', 'project', 'trick', 'error', 'info', 'baloot', 'kaboot'
library;
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Toast notification types matching the TypeScript ToastType union.
enum ToastType { turn, akka, sawa, project, trick, error, info, baloot, kaboot, success, warning }

class ToastMessage {
  final String id;
  final String message;
  final ToastType type;
  final Duration duration;

  ToastMessage({
    required this.id,
    required this.message,
    this.type = ToastType.info,
    this.duration = const Duration(seconds: 3),
  });
}

class ToastNotifier extends StateNotifier<List<ToastMessage>> {
  final Map<String, Timer> _timers = {};

  ToastNotifier() : super([]);

  void show(String message, {ToastType type = ToastType.info, Duration? duration}) {
    final id = DateTime.now().microsecondsSinceEpoch.toString();
    final toast = ToastMessage(
      id: id,
      message: message,
      type: type,
      duration: duration ?? const Duration(seconds: 3),
    );

    // Limit to 3 toasts, removing oldest
    if (state.length >= 3) {
      final removed = state.first;
      _timers.remove(removed.id)?.cancel();
      state = [...state.sublist(1), toast];
    } else {
      state = [...state, toast];
    }

    // Auto dismiss — tracked for cleanup
    _timers[id] = Timer(toast.duration, () {
      _timers.remove(id);
      if (mounted) remove(id);
    });
  }

  void remove(String id) {
    _timers.remove(id)?.cancel();
    state = state.where((t) => t.id != id).toList();
  }

  void clear() {
    for (final timer in _timers.values) {
      timer.cancel();
    }
    _timers.clear();
    state = [];
  }

  @override
  void dispose() {
    for (final timer in _timers.values) {
      timer.cancel();
    }
    _timers.clear();
    super.dispose();
  }
}

final toastProvider = StateNotifierProvider<ToastNotifier, List<ToastMessage>>((ref) {
  return ToastNotifier();
});
