/// emote_notifier.dart — Emote and flying item system.
///
/// Port of frontend/src/hooks/useEmotes.ts (59 lines).
///
/// Manages the emote menu state and flying item animations.
/// Players can send emotes that appear as flying items on screen.
///
/// ## Emote Types
/// Standard emojis + Baloot-specific items (teapot, shay, dates).
///
/// ## Socket Integration
/// When socket emote events are added to SocketService, the
/// _subscribeToSocket method will wire them up.
library;
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

/// A flying emote item on screen.
class FlyingEmote {
  final String id;
  final String emoji;
  final int senderIndex;
  final int targetIndex;
  final DateTime createdAt;

  FlyingEmote({
    required this.id,
    required this.emoji,
    required this.senderIndex,
    required this.targetIndex,
    DateTime? createdAt,
  }) : createdAt = createdAt ?? DateTime.now();
}

/// Emote menu and flying items state.
class EmoteState {
  /// Whether the emote picker menu is open.
  final bool isMenuOpen;

  /// Currently flying emotes on screen.
  final List<FlyingEmote> flyingEmotes;

  const EmoteState({
    this.isMenuOpen = false,
    this.flyingEmotes = const [],
  });

  EmoteState copyWith({
    bool? isMenuOpen,
    List<FlyingEmote>? flyingEmotes,
  }) {
    return EmoteState(
      isMenuOpen: isMenuOpen ?? this.isMenuOpen,
      flyingEmotes: flyingEmotes ?? this.flyingEmotes,
    );
  }
}

/// Manages emote sending, receiving, and flying item lifecycle.
class EmoteNotifier extends StateNotifier<EmoteState> {
  EmoteNotifier() : super(const EmoteState());

  /// Toggle the emote picker menu.
  void toggleMenu() {
    state = state.copyWith(isMenuOpen: !state.isMenuOpen);
  }

  /// Close the emote picker menu.
  void closeMenu() {
    state = state.copyWith(isMenuOpen: false);
  }

  /// Send an emote (locally for now; socket wiring in M-F4).
  void sendEmote(String emoji, {int targetIndex = -1}) {
    closeMenu();
    // Show locally
    _addFlyingEmote(emoji, 0, targetIndex);
  }

  /// Receive an emote from a remote player.
  void receiveEmote(String emoji, int senderIdx) {
    _addFlyingEmote(emoji, senderIdx, 0);
  }

  /// Add a flying emote that auto-removes after 2 seconds.
  void _addFlyingEmote(String emoji, int senderIdx, int targetIdx) {
    final emote = FlyingEmote(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      emoji: emoji,
      senderIndex: senderIdx,
      targetIndex: targetIdx,
    );

    state = state.copyWith(
      flyingEmotes: [...state.flyingEmotes, emote],
    );

    // Auto-remove after 2 seconds
    Timer(const Duration(seconds: 2), () {
      if (!mounted) return;
      state = state.copyWith(
        flyingEmotes:
            state.flyingEmotes.where((e) => e.id != emote.id).toList(),
      );
    });
  }
}

final emoteProvider =
    StateNotifierProvider<EmoteNotifier, EmoteState>((ref) {
  return EmoteNotifier();
});
