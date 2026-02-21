/// bot_turn_handler.dart — Local bot AI for offline play.
///
/// Watches game state and auto-plays for bot players (index 1, 2, 3)
/// during offline games. Uses simple heuristics:
/// - Bidding: 40% chance to bid (SUN or HOKUM), else PASS
/// - Playing: plays the first valid card
///
/// This is a lightweight stand-in for the Python AI backend.
library;

import 'dart:async';
import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/enums.dart';
import '../utils/trick_utils.dart';
import 'providers.dart';

/// Provider that creates and manages the bot turn handler.
final botTurnHandlerProvider = Provider.autoDispose<BotTurnHandler>((ref) {
  final handler = BotTurnHandler(ref);
  ref.onDispose(() => handler.dispose());
  return handler;
});

/// Handles bot turns in offline mode.
class BotTurnHandler {
  final Ref _ref;
  final _rng = Random();
  Timer? _botTimer;
  bool _disposed = false;

  BotTurnHandler(this._ref);

  /// Check if it's a bot's turn and schedule a move.
  /// Also handles trick transitions and project reveals.
  void checkAndScheduleBotTurn() {
    if (_disposed) {
      print('[BOT] BotHandler: disposed, skipping');
      return;
    }
    _botTimer?.cancel();

    final gs = _ref.read(gameStateProvider).gameState;
    print('[BOT] phase=${gs.phase}, turn=${gs.currentTurnIndex}, trick=${gs.isTrickTransitioning}, proj=${gs.isProjectRevealing}, round=${gs.isRoundTransitioning}');

    // Handle trick transition (4 cards on table)
    if (gs.isTrickTransitioning == true) {
      _botTimer = Timer(const Duration(milliseconds: 800), () {
        if (_disposed) return;
        _ref.read(roundManagerProvider.notifier).completeTrick();
      });
      return;
    }

    // Handle project reveal animation
    if (gs.isProjectRevealing == true) {
      _botTimer = Timer(const Duration(milliseconds: 1200), () {
        if (_disposed) return;
        _ref.read(roundManagerProvider.notifier).clearProjectReveal();
      });
      return;
    }

    // Skip during round transitions (round_manager handles these)
    if (gs.isRoundTransitioning == true) return;

    final idx = gs.currentTurnIndex;

    // Only act for bot players in bidding or playing phase
    if (idx < 0 || idx >= gs.players.length) return;
    if (!gs.players[idx].isBot) return;
    if (gs.phase != GamePhase.bidding && gs.phase != GamePhase.playing) return;

    // Delay to simulate thinking (400-900ms)
    final delay = 400 + _rng.nextInt(500);
    _botTimer = Timer(Duration(milliseconds: delay), () {
      if (_disposed) return;
      _executeBotTurn();
    });
  }

  void _executeBotTurn() {
    if (_disposed) return;

    final gs = _ref.read(gameStateProvider).gameState;
    final idx = gs.currentTurnIndex;

    if (idx < 0 || idx >= gs.players.length) return;
    if (!gs.players[idx].isBot) return;

    print('[BOT] executing turn for player $idx (${gs.players[idx].name}), phase=${gs.phase}');

    if (gs.phase == GamePhase.bidding) {
      _botBid(idx);
    } else if (gs.phase == GamePhase.playing) {
      _botPlay(idx);
    }
  }

  /// Bot bidding: simple heuristic.
  void _botBid(int playerIndex) {
    final gs = _ref.read(gameStateProvider).gameState;
    final hand = gs.players[playerIndex].hand;

    // Count high cards (A, K, 10) and face cards
    int highCards = 0;
    for (final c in hand) {
      if (c.rank == 'A' || c.rank == 'K' || c.rank == '10') highCards++;
    }

    // Round 1: bid if 3+ high cards (else pass)
    // Round 2: bid if 2+ high cards (more aggressive, to avoid gash)
    final threshold = gs.biddingRound == 1 ? 3 : 2;
    final shouldBid = highCards >= threshold;

    if (shouldBid) {
      // Prefer HOKUM if floor card suit matches a strong holding
      final floorSuit = gs.floorCard?.suit;
      int floorSuitCount = 0;
      if (floorSuit != null) {
        for (final c in hand) {
          if (c.suit == floorSuit) floorSuitCount++;
        }
      }

      String action;
      Map<String, dynamic>? payload;

      if (floorSuitCount >= 2 && gs.biddingRound == 1) {
        action = 'HOKUM';
      } else if (gs.biddingRound == 2) {
        // R2: pick the most frequent suit for HOKUM, or SUN
        if (_rng.nextBool()) {
          action = 'SUN';
        } else {
          action = 'HOKUM';
          // Pick most common suit
          final suitCounts = <Suit, int>{};
          for (final c in hand) {
            suitCounts[c.suit] = (suitCounts[c.suit] ?? 0) + 1;
          }
          Suit bestSuit = Suit.spades;
          int bestCount = 0;
          for (final e in suitCounts.entries) {
            if (e.value > bestCount) {
              bestCount = e.value;
              bestSuit = e.key;
            }
          }
          payload = {'suit': bestSuit};
        }
      } else {
        action = _rng.nextBool() ? 'SUN' : 'HOKUM';
      }

      _ref.read(biddingLogicProvider.notifier).handleBiddingAction(
            playerIndex,
            action,
            payload: payload,
          );
    } else {
      _ref.read(biddingLogicProvider.notifier).handleBiddingAction(
            playerIndex,
            'PASS',
          );
    }
  }

  /// Bot play: pick a valid card (simple: first valid).
  void _botPlay(int playerIndex) {
    final gs = _ref.read(gameStateProvider).gameState;
    final hand = gs.players[playerIndex].hand;
    if (hand.isEmpty) return;

    final trumpSuit = gs.bid.type == GameMode.hokum
        ? (gs.bid.suit ?? gs.floorCard?.suit)
        : null;
    final mode =
        gs.bid.type == GameMode.sun ? GameMode.sun : GameMode.hokum;

    // Find first valid card
    int validIndex = 0;
    for (int i = 0; i < hand.length; i++) {
      if (isValidMove(
        card: hand[i],
        hand: hand,
        tableCards: gs.tableCards,
        mode: mode,
        trumpSuit: trumpSuit,
        isLocked: gs.isLocked,
      )) {
        validIndex = i;
        break;
      }
    }

    _ref.read(playingLogicProvider.notifier).handleCardPlay(
          playerIndex,
          validIndex,
        );
  }

  void dispose() {
    _disposed = true;
    _botTimer?.cancel();
  }
}
