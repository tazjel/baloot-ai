/// bidding_logic.dart — Bid phase action handler.
///
/// Port of frontend/src/hooks/useBiddingLogic.ts (152 lines).
///
/// Handles all bidding actions (PASS, SUN, HOKUM, ASHKAL) for
/// offline/local play. When connected to server, the server handles
/// bidding — this is only used for the local game.
///
/// ## Bidding Flow
/// 1. Round 1: Players can PASS, SUN, HOKUM (floor card suit), or ASHKAL
/// 2. If all pass in R1 → Round 2 (dealer says "thany")
/// 3. Round 2: HOKUM with chosen suit, or SUN
/// 4. If all pass in R2 → Gash (redeal with dealer rotation)
///
/// ## On Successful Bid
/// - Floor card goes to bidder (or partner for ASHKAL)
/// - Remaining deck cards distributed (bidder gets 2, others get 3)
/// - Hands sorted by mode
/// - Projects detected for all players
/// - Phase transitions to Playing
library;
import 'dart:async';
import 'dart:developer' as dev;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/card_model.dart';
import '../models/declared_project.dart';
import '../models/enums.dart';
import '../models/bid.dart';
import '../utils/project_utils.dart';
import '../utils/sort_utils.dart';
import 'providers.dart';

/// Handles bidding phase actions.
///
/// Stateless notifier (void state) — operates on the master
/// [GameStateNotifier] for all state mutations.
class BiddingLogicNotifier extends StateNotifier<void> {
  final Ref _ref;

  /// Timer for redeal delay (Gash: all players passed both rounds).
  Timer? _redealTimer;

  BiddingLogicNotifier(this._ref) : super(null);

  /// Handle a bidding action from a player.
  ///
  /// [playerIndex] is the seat index (0-3) of the player.
  /// [action] is one of: 'PASS', 'SUN', 'HOKUM', 'ASHKAL'.
  /// [payload] may contain 'suit' for R2 HOKUM picks.
  void handleBiddingAction(
    int playerIndex,
    String action, {
    Map<String, dynamic>? payload,
  }) {
    dev.log('Bidding: $action by player $playerIndex', name: 'BIDDING');

    final gameNotifier = _ref.read(gameStateProvider.notifier);

    gameNotifier.updateGameState((prev) {
      // Guard: player must be active
      if (playerIndex < 0 || playerIndex >= prev.players.length) return prev;
      if (!prev.players[playerIndex].isActive) return prev;

      final players = List.generate(prev.players.length, (i) {
        return prev.players[i].copyWith(
          hand: List<CardModel>.from(prev.players[i].hand),
        );
      });

      // Kawesh (worthless hand redeal) — pre-bid: same dealer, post-bid: rotate
      if (action == 'KAWESH') {
        gameNotifier.addSystemMessage(
          '${prev.players[playerIndex].name} أعلن كوش! توزيع جديد...',
        );
        final scores = prev.matchScores;
        final dealerIdx = prev.dealerIndex;
        _redealTimer?.cancel();
        _redealTimer = Timer(const Duration(milliseconds: 1500), () {
          _redealTimer = null;
          _ref.read(roundManagerProvider.notifier).startNewRound(
                nextDealerIndex: dealerIdx, // Kawesh = same dealer
                matchScores: scores,
              );
        });
        return prev;
      }

      // Set action text on bidding player
      final actionText = action == 'PASS'
          ? 'بس'
          : action == 'SUN'
              ? 'صن'
              : action == 'HOKUM'
                  ? 'حكم'
                  : action == 'ASHKAL'
                      ? 'أشكال'
                      : action;
      players[playerIndex] =
          players[playerIndex].copyWith(actionText: actionText, isActive: false);

      int nextIndex = (playerIndex + 1) % 4;
      Bid newBid = prev.bid;
      GamePhase newPhase = prev.phase;
      int newRound = prev.biddingRound;
      final dealerIdx = prev.dealerIndex;
      final firstBidderIdx = (dealerIdx + 1) % 4;

      if (action == 'PASS') {
        // Check if all players have passed
        if (nextIndex == firstBidderIdx) {
          if (prev.biddingRound == 1) {
            // Move to Round 2
            newRound = 2;
            gameNotifier.addSystemMessage('الجولة الثانية من الشراء');
          } else {
            // Gash: all passed both rounds → redeal
            gameNotifier.addSystemMessage('قش! الجميع باسوا. توزيع جديد...');
            _redealTimer?.cancel();
            final scores = prev.matchScores;
            _redealTimer = Timer(const Duration(milliseconds: 1500), () {
              _redealTimer = null;
              _ref.read(roundManagerProvider.notifier).startNewRound(
                    nextDealerIndex: (dealerIdx + 1) % 4,
                    matchScores: scores,
                  );
            });
            return prev;
          }
        }
      } else {
        // --- Successful bid: SUN, HOKUM, or ASHKAL ---
        String actualAction = action;
        int pickupIndex = playerIndex;

        if (action == 'ASHKAL') {
          actualAction = 'SUN';
          pickupIndex = (playerIndex + 2) % 4; // Partner picks up floor card
          players[playerIndex] =
              players[playerIndex].copyWith(actionText: 'أشكال');
        }

        // Determine trump suit
        Suit? selectedSuit;
        if (actualAction == 'HOKUM') {
          if (prev.biddingRound == 1 && prev.floorCard != null) {
            selectedSuit = prev.floorCard!.suit;
          } else if (prev.biddingRound == 2 && payload?['suit'] != null) {
            final suitStr = payload!['suit'];
            if (suitStr is Suit) {
              selectedSuit = suitStr;
            } else if (suitStr is String) {
              selectedSuit = Suit.fromSymbol(suitStr);
            }
          }
          selectedSuit ??= Suit.spades;
        }

        // Build bid
        final bidType =
            actualAction == 'SUN' ? GameMode.sun : GameMode.hokum;
        newBid = Bid(
          type: bidType,
          suit: selectedSuit,
          bidder: players[playerIndex].position,
        );

        // Floor card goes to pickup player
        if (prev.floorCard != null) {
          final updatedHand = [
            ...players[pickupIndex].hand,
            prev.floorCard!,
          ];
          players[pickupIndex] =
              players[pickupIndex].copyWith(hand: updatedHand);
        }

        // Distribute remaining deck cards
        final remainingDeck = prev.deck.sublist(21.clamp(0, prev.deck.length));
        int deckPointer = 0;
        for (int i = 0; i < 4; i++) {
          final pIdx = (dealerIdx + 1 + i) % 4;
          final count = (pIdx == pickupIndex) ? 2 : 3;
          for (int k = 0; k < count && deckPointer < remainingDeck.length; k++) {
            final newHand = [...players[pIdx].hand, remainingDeck[deckPointer++]];
            players[pIdx] = players[pIdx].copyWith(hand: newHand);
          }
        }

        // Sort all hands by game mode
        final mode =
            actualAction == 'SUN' ? GameMode.sun : GameMode.hokum;
        for (int i = 0; i < players.length; i++) {
          players[i] = players[i].copyWith(
            hand: sortHand(players[i].hand, mode, selectedSuit),
          );
        }

        gameNotifier.addSystemMessage(
          '${players[playerIndex].name} اشترى ${actualAction == "SUN" ? "صن" : "حكم"}',
        );
        newPhase = GamePhase.playing;

        // Detect projects for all players
        final trumpSuit = bidType == GameMode.sun ? null : selectedSuit;
        final newDeclarations = <String, List<DeclaredProject>>{};
        bool hasAnyProjects = false;
        for (final p in players) {
          final projects = detectProjects(p.hand, p.position, trumpSuit);
          newDeclarations[p.position.value] = projects;
          if (projects.isNotEmpty) hasAnyProjects = true;
        }

        // First player after dealer leads
        nextIndex = (dealerIdx + 1) % 4;
        for (int i = 0; i < players.length; i++) {
          players[i] = players[i].copyWith(isActive: i == nextIndex);
        }

        return prev.copyWith(
          players: players,
          currentTurnIndex: nextIndex,
          bid: newBid,
          phase: newPhase,
          biddingRound: newRound,
          declarations: newDeclarations,
          isProjectRevealing: hasAnyProjects,
          floorCard: null,
        );
      }

      // PASS: activate next player
      players[nextIndex] = players[nextIndex].copyWith(isActive: true);

      return prev.copyWith(
        players: players,
        currentTurnIndex: nextIndex,
        biddingRound: newRound,
      );
    });
  }

  @override
  void dispose() {
    _redealTimer?.cancel();
    super.dispose();
  }
}
