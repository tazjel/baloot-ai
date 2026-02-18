/// round_manager.dart — Round lifecycle and trick completion.
///
/// Port of frontend/src/hooks/useRoundManager.ts (286 lines).
///
/// Manages the complete lifecycle of a Baloot round:
/// - New round setup (deck generation, card distribution, floor card)
/// - Trick completion (winner calculation, points, round transitions)
/// - Transition timers (lastTrick display, project reveals, akka)
/// - Round scoring via AccountingEngine
///
/// ## Trick Completion Flow
/// 1. 4 cards on table → isTrickTransitioning = true
/// 2. Calculate trick winner using getTrickWinner()
/// 3. Accumulate raw trick points
/// 4. If last trick: calculate round result, check for match end (152 GP)
/// 5. If not last: store lastTrick, advance to winner's turn
///
/// ## Important Note
/// When connected to the server (roomId != null), the server handles round
/// management. This logic is only used for local/offline play.
library;
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/enums.dart';
import '../models/game_settings.dart';
import '../models/game_state.dart';
import '../models/player.dart';
import '../models/bid.dart';
import '../models/round_result.dart';
import '../services/accounting_engine.dart';
import '../utils/deck_utils.dart';
import '../utils/project_utils.dart';
import '../utils/scoring_utils.dart';
import '../utils/sort_utils.dart';
import '../utils/trick_utils.dart';
import 'providers.dart';

/// Manages round lifecycle: new rounds, trick completion, scoring.
///
/// This notifier is stateless (void) — it operates on the master
/// [GameStateNotifier] for all state mutations.
class RoundManager extends StateNotifier<void> {
  final Ref _ref;

  /// Timer for delayed round transitions (1.5s between rounds).
  Timer? _roundTransitionTimer;

  RoundManager(this._ref) : super(null);

  // =========================================================================
  // Start New Round
  // =========================================================================

  /// Start a new round with the given dealer index.
  ///
  /// Generates a shuffled deck, distributes 5 cards to each player,
  /// sets the floor card (card at index 20), resets bidding state,
  /// and transitions to the Bidding phase.
  ///
  /// Parameters:
  /// - [nextDealerIndex]: The seat index of the dealer for this round (0-3)
  /// - [matchScores]: Current match scores to preserve across rounds
  /// - [newSettings]: Optional settings override for this round
  void startNewRound({
    int nextDealerIndex = 3,
    TeamScores? matchScores,
    GameSettings? newSettings,
  }) {
    final gameNotifier = _ref.read(gameStateProvider.notifier);
    final prevState = gameNotifier.gameState;
    final scores = matchScores ?? prevState.matchScores;

    // Generate and shuffle deck
    final deck = generateDeck();

    // Distribute initial 5 cards per player
    final p0Hand = sortHand(deck.sublist(0, 5), GameMode.hokum);
    final p1Hand = sortHand(deck.sublist(5, 10), GameMode.hokum);
    final p2Hand = sortHand(deck.sublist(10, 15), GameMode.hokum);
    final p3Hand = sortHand(deck.sublist(15, 20), GameMode.hokum);
    final floorCard = deck[20];
    final firstTurn = (nextDealerIndex + 1) % 4;

    gameNotifier.updateGameState((prev) {
      final players = List.generate(prev.players.length, (i) {
        final p = prev.players[i];
        final hand = i == 0
            ? p0Hand
            : i == 1
                ? p1Hand
                : i == 2
                    ? p2Hand
                    : p3Hand;
        return p.copyWith(
          hand: hand,
          isDealer: i == nextDealerIndex,
          actionText: null,
          isActive: i == firstTurn,
        );
      });

      return prev.copyWith(
        players: players,
        matchScores: scores,
        phase: GamePhase.bidding,
        currentTurnIndex: firstTurn,
        dealerIndex: nextDealerIndex,
        biddingRound: 1,
        floorCard: floorCard,
        tableCards: [],
        deck: deck,
        bid: const Bid.empty(),
        declarations: {},
        doublingLevel: DoublingLevel.normal,
        roundHistory: prev.roundHistory,
        isLocked: false,
        isRoundTransitioning: false,
        isTrickTransitioning: false,
        isProjectRevealing: false,
        isFastForwarding: false,
        settings: newSettings ?? prev.settings,
      );
    });

    final safeDealerIdx =
        (nextDealerIndex >= 0 && nextDealerIndex < 4) ? nextDealerIndex : 0;
    final dealerName = gameNotifier.gameState.players.length > safeDealerIdx
        ? gameNotifier.gameState.players[safeDealerIdx].name
        : 'Unknown';
    gameNotifier.addSystemMessage('تم قص الورق (سقا) - الموزع: $dealerName');
    gameNotifier.addSystemMessage('بدأت الجولة');
  }

  // =========================================================================
  // Trick Completion
  // =========================================================================

  /// Complete the current trick after all 4 cards are played.
  ///
  /// Calculates the trick winner, accumulates points, and either:
  /// - Transitions to the next trick (if cards remain)
  /// - Calculates round result and transitions to next round or game over
  void completeTrick() {
    final gameNotifier = _ref.read(gameStateProvider.notifier);

    gameNotifier.updateGameState((prev) {
      if (prev.tableCards.length != 4) {
        return prev.copyWith(isTrickTransitioning: false);
      }

      final tableCards = prev.tableCards;
      final players = List<Player>.from(prev.players);

      // Determine trump suit
      final isSun = prev.bid.type == GameMode.sun;
      final trumpSuit = isSun ? null : (prev.bid.suit ?? prev.floorCard?.suit);
      final mode = isSun ? GameMode.sun : GameMode.hokum;

      // Calculate trick winner
      final winIdx = getTrickWinner(tableCards, mode, trumpSuit);
      if (winIdx < 0) return prev.copyWith(isTrickTransitioning: false);
      final winnerPos = tableCards[winIdx].playedBy;
      final winningPlayerIndex =
          players.indexWhere((p) => p.position == winnerPos);
      if (winningPlayerIndex < 0) return prev.copyWith(isTrickTransitioning: false);
      final isUs = winningPlayerIndex == 0 || winningPlayerIndex == 2;

      // Calculate raw trick points
      int rawTrickPoints = 0;
      for (final tc in tableCards) {
        rawTrickPoints += getCardPointValue(tc.card, mode);
      }

      // Last trick bonus: +10 points
      final isLastTrick = players.every((p) => p.hand.isEmpty);
      if (isLastTrick) rawTrickPoints += 10;

      final currentUsRaw =
          prev.teamScores.us + (isUs ? rawTrickPoints : 0);
      final currentThemRaw =
          prev.teamScores.them + (!isUs ? rawTrickPoints : 0);

      // Update active player
      for (int i = 0; i < players.length; i++) {
        players[i] = players[i].copyWith(isActive: i == winningPlayerIndex);
      }

      if (isLastTrick) {
        return _handleLastTrick(
          prev: prev,
          players: players,
          currentUsRaw: currentUsRaw,
          currentThemRaw: currentThemRaw,
          mode: mode,
        );
      }

      // Mid-round: store lastTrick and advance to winner's turn
      final lastTrickData = <String, dynamic>{
        'cards': tableCards.map((tc) => {
              'card': tc.card.toJson(),
              'playedBy': tc.playedBy.value,
            }).toList(),
        'winner': winnerPos.value,
      };

      return prev.copyWith(
        players: players,
        tableCards: [],
        teamScores: TeamScores(us: currentUsRaw, them: currentThemRaw),
        currentTurnIndex: winningPlayerIndex,
        isTrickTransitioning: false,
        lastTrick: lastTrickData,
      );
    });
  }

  /// Handle the last trick of a round — calculate scoring and transition.
  GameState _handleLastTrick({
    required GameState prev,
    required List<Player> players,
    required int currentUsRaw,
    required int currentThemRaw,
    required GameMode mode,
  }) {
    // Resolve project conflicts
    final resolvedDeclarations = resolveProjectConflicts(prev.declarations, mode);

    // Calculate project points per team
    int usProjectPoints = 0;
    int themProjectPoints = 0;

    for (final entry in resolvedDeclarations.entries) {
      final pos = entry.key;
      final isUsPlayer = pos == PlayerPosition.bottom.value ||
          pos == PlayerPosition.top.value;

      for (final proj in entry.value) {
        final val = getProjectScoreValue(proj.type, mode);
        if (isUsPlayer) {
          usProjectPoints += val;
        } else {
          themProjectPoints += val;
        }
      }
    }

    // Determine bidder team
    final bidderPos = prev.bid.bidder;
    String? bidderTeam;
    if (bidderPos == PlayerPosition.bottom ||
        bidderPos == PlayerPosition.top) {
      bidderTeam = 'us';
    } else if (bidderPos == PlayerPosition.right ||
        bidderPos == PlayerPosition.left) {
      bidderTeam = 'them';
    }

    // Calculate round result using AccountingEngine
    final modeStr = mode == GameMode.sun ? 'SUN' : 'HOKUM';
    final result = AccountingEngine.calculateRoundResult(
      usRaw: currentUsRaw,
      themRaw: currentThemRaw,
      usProjects: usProjectPoints,
      themProjects: themProjectPoints,
      bidType: modeStr,
      doublingLevel: prev.doublingLevel,
      bidderTeam: bidderTeam,
    );

    // Build round result from RoundScoreResult
    final usDetailed = DetailedScore(
      mashaari: result.us.projectPoints,
      abnat: result.us.rawCardPoints,
      gamePoints: result.us.gamePoints,
      result: result.us.gamePoints,
    );
    final themDetailed = DetailedScore(
      mashaari: result.them.projectPoints,
      abnat: result.them.rawCardPoints,
      gamePoints: result.them.gamePoints,
      result: result.them.gamePoints,
    );

    final newHistory = [
      ...prev.roundHistory,
      RoundResult(
        roundNumber: prev.roundHistory.length + 1,
        us: usDetailed,
        them: themDetailed,
        winner: result.winner,
        gameMode: prev.bid.type?.value,
      ),
    ];

    final globalUs = prev.matchScores.us + result.us.gamePoints;
    final globalThem = prev.matchScores.them + result.them.gamePoints;

    // Check for match end (152 GP threshold)
    if (globalUs >= 152 || globalThem >= 152) {
      return prev.copyWith(
        phase: GamePhase.gameOver,
        matchScores: TeamScores(us: globalUs, them: globalThem),
        roundHistory: newHistory,
        tableCards: [],
        isTrickTransitioning: false,
      );
    }

    // Schedule round transition (1.5s delay)
    _roundTransitionTimer?.cancel();
    _roundTransitionTimer = Timer(const Duration(milliseconds: 1500), () {
      _roundTransitionTimer = null;
      startNewRound(
        nextDealerIndex: (prev.dealerIndex + 1) % 4,
        matchScores: TeamScores(us: globalUs, them: globalThem),
      );
    });

    return prev.copyWith(
      teamScores: TeamScores(us: currentUsRaw, them: currentThemRaw),
      matchScores: TeamScores(us: globalUs, them: globalThem),
      roundHistory: newHistory,
      tableCards: [],
      isRoundTransitioning: true,
    );
  }

  // =========================================================================
  // Transition Helpers
  // =========================================================================

  /// Clear the lastTrick display after a delay.
  void clearLastTrickAfterDelay() {
    Timer(const Duration(seconds: 1), () {
      if (!mounted) return;
      _ref.read(gameStateProvider.notifier).updateGameState((prev) {
        return prev.copyWith(lastTrick: null);
      });
    });
  }

  /// Handle trick transition: delay then call completeTrick.
  void handleTrickTransition() {
    Timer(const Duration(milliseconds: 600), () {
      if (!mounted) return;
      completeTrick();
    });
  }

  /// Clear project reveal flag after animation completes.
  void clearProjectReveal() {
    Timer(const Duration(milliseconds: 800), () {
      if (!mounted) return;
      _ref.read(gameStateProvider.notifier).updateGameState((prev) {
        return prev.copyWith(isProjectRevealing: false);
      });
    });
  }

  // =========================================================================
  // Lifecycle
  // =========================================================================

  @override
  void dispose() {
    _roundTransitionTimer?.cancel();
    super.dispose();
  }
}
