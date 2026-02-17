import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/game_state.dart';

class ReplayState {
  final bool isActive;
  final bool isPlaying;
  final int currentIndex;
  final int totalSteps;
  final List<GameState> history;
  final double playbackSpeed; // 1.0 = 1 sec/step

  const ReplayState({
    this.isActive = false,
    this.isPlaying = false,
    this.currentIndex = 0,
    this.totalSteps = 0,
    this.history = const [],
    this.playbackSpeed = 1.0,
  });

  GameState? get currentState => 
      history.isNotEmpty && currentIndex < history.length 
          ? history[currentIndex] 
          : null;

  ReplayState copyWith({
    bool? isActive,
    bool? isPlaying,
    int? currentIndex,
    int? totalSteps,
    List<GameState>? history,
    double? playbackSpeed,
  }) {
    return ReplayState(
      isActive: isActive ?? this.isActive,
      isPlaying: isPlaying ?? this.isPlaying,
      currentIndex: currentIndex ?? this.currentIndex,
      totalSteps: totalSteps ?? this.totalSteps,
      history: history ?? this.history,
      playbackSpeed: playbackSpeed ?? this.playbackSpeed,
    );
  }
}

class ReplayNotifier extends StateNotifier<ReplayState> {
  Timer? _timer;

  ReplayNotifier() : super(const ReplayState());

  void startReplay(List<GameState> history) {
    if (history.isEmpty) return;
    
    // Sort history by turn index or timestamp if needed, assume mapped correctly
    state = ReplayState(
      isActive: true,
      isPlaying: false,
      currentIndex: 0,
      totalSteps: history.length,
      history: history,
    );
  }

  void exitReplay() {
    _stopTimer();
    state = const ReplayState(isActive: false);
  }

  void togglePlay() {
    if (state.isPlaying) {
      pause();
    } else {
      play();
    }
  }

  void play() {
    if (!state.isActive) return;
    if (state.currentIndex >= state.totalSteps - 1) {
      // Restart if at end
      jumpTo(0);
    }
    
    state = state.copyWith(isPlaying: true);
    _startTimer();
  }

  void pause() {
    _stopTimer();
    state = state.copyWith(isPlaying: false);
  }

  void next() {
    if (state.currentIndex < state.totalSteps - 1) {
      state = state.copyWith(currentIndex: state.currentIndex + 1);
    } else {
      pause(); // Stop if at end
    }
  }

  void previous() {
     if (state.currentIndex > 0) {
      state = state.copyWith(currentIndex: state.currentIndex - 1);
    }
  }

  void jumpTo(int index) {
    if (index >= 0 && index < state.totalSteps) {
      state = state.copyWith(currentIndex: index);
    }
  }

  void setSpeed(double speed) {
    state = state.copyWith(playbackSpeed: speed);
    if (state.isPlaying) {
      _stopTimer();
      _startTimer();
    }
  }

  void _startTimer() {
    _stopTimer();
    final durationMs = (1000 / state.playbackSpeed).round();
    _timer = Timer.periodic(Duration(milliseconds: durationMs), (_) {
      next();
    });
  }

  void _stopTimer() {
    _timer?.cancel();
    _timer = null;
  }

  @override
  void dispose() {
    _stopTimer();
    super.dispose();
  }
}

final replayProvider = StateNotifierProvider<ReplayNotifier, ReplayState>((ref) {
  return ReplayNotifier();
});
