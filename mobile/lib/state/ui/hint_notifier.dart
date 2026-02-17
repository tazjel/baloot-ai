/// hint_notifier.dart — AI hint system.
///
/// Port of frontend/src/hooks/useHintSystem.ts (50 lines).
///
/// Provides on-demand AI hints to the human player, showing
/// recommended card and reasoning in Arabic.
///
/// ## Hint Flow
/// 1. Player taps hint button
/// 2. Notifier requests hint from server (or computes locally)
/// 3. Highlighted card index + reasoning text shown
/// 4. Hint auto-clears after 5 seconds or when card is played
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Current hint state.
class HintState {
  /// Whether a hint is currently showing.
  final bool isActive;

  /// Whether a hint request is in progress.
  final bool isLoading;

  /// Index of the recommended card in the player's hand.
  final int? recommendedCardIndex;

  /// Arabic reasoning text explaining the recommendation.
  final String? reasoning;

  const HintState({
    this.isActive = false,
    this.isLoading = false,
    this.recommendedCardIndex,
    this.reasoning,
  });

  HintState copyWith({
    bool? isActive,
    bool? isLoading,
    int? recommendedCardIndex,
    String? reasoning,
  }) {
    return HintState(
      isActive: isActive ?? this.isActive,
      isLoading: isLoading ?? this.isLoading,
      recommendedCardIndex: recommendedCardIndex ?? this.recommendedCardIndex,
      reasoning: reasoning ?? this.reasoning,
    );
  }
}

/// Manages AI hint requests and display.
class HintNotifier extends StateNotifier<HintState> {
  Timer? _autoClearTimer;

  HintNotifier() : super(const HintState());

  /// Request a hint (placeholder — will wire to SocketService in M-F4).
  ///
  /// For now, use [setHint] to provide hints directly.
  Future<void> requestHint() async {
    if (state.isLoading || state.isActive) return;

    state = state.copyWith(isLoading: true);

    // TODO: Wire to SocketService.requestHint() when available
    // For now, just show loading briefly then reset
    await Future.delayed(const Duration(milliseconds: 300));

    if (!mounted) return;
    state = const HintState(); // Reset — no hint available yet
  }

  /// Clear the current hint.
  void clearHint() {
    _autoClearTimer?.cancel();
    _autoClearTimer = null;
    if (mounted) {
      state = const HintState();
    }
  }

  /// Set a hint directly (for offline/local mode or server response).
  void setHint(int cardIndex, String reasoning) {
    state = HintState(
      isActive: true,
      isLoading: false,
      recommendedCardIndex: cardIndex,
      reasoning: reasoning,
    );

    _autoClearTimer?.cancel();
    _autoClearTimer = Timer(const Duration(seconds: 5), () {
      clearHint();
    });
  }

  @override
  void dispose() {
    _autoClearTimer?.cancel();
    super.dispose();
  }
}

final hintProvider =
    StateNotifierProvider<HintNotifier, HintState>((ref) {
  return HintNotifier();
});
