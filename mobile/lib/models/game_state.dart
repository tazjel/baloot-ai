/// GameState — Complete game state model.
///
/// Port of frontend/src/types.ts GameState interface.
import 'bid.dart';
import 'card_model.dart';
import 'declared_project.dart';
import 'enums.dart';
import 'game_settings.dart';
import 'player.dart';
import 'round_result.dart';

class SawaState {
  final bool active;
  final PlayerPosition? claimer;
  final Map<String, String> responses; // position -> 'ACCEPT'|'REFUSE'
  final SawaStatus status;
  final bool challengeActive;

  const SawaState({
    this.active = false,
    this.claimer,
    this.responses = const {},
    this.status = SawaStatus.none,
    this.challengeActive = false,
  });

  factory SawaState.fromJson(Map<String, dynamic> json) {
    return SawaState(
      active: json['active'] as bool? ?? false,
      claimer: json['claimer'] != null
          ? PlayerPosition.fromValue(json['claimer'] as String)
          : null,
      responses: (json['responses'] as Map<String, dynamic>?)
              ?.map((k, v) => MapEntry(k, v as String)) ??
          {},
      status: SawaStatus.fromValue(json['status'] as String? ?? 'NONE'),
      challengeActive: json['challenge_active'] as bool? ?? false,
    );
  }
}

class QaydState {
  final bool active;
  final QaydStep? step;
  final PlayerPosition? reporter;
  final bool? reporterIsBot;
  final String? menuOption;
  final String? violationType;
  final CardModel? crimeCard;
  final CardModel? proofCard;
  final String? verdict;
  final String? verdictMessage;
  final String? loserTeam;
  final int? penaltyPoints;
  final int? timerDuration;
  final int? timerStart;
  final String? reason;
  final String? status;

  const QaydState({
    this.active = false,
    this.step,
    this.reporter,
    this.reporterIsBot,
    this.menuOption,
    this.violationType,
    this.crimeCard,
    this.proofCard,
    this.verdict,
    this.verdictMessage,
    this.loserTeam,
    this.penaltyPoints,
    this.timerDuration,
    this.timerStart,
    this.reason,
    this.status,
  });

  factory QaydState.fromJson(Map<String, dynamic> json) {
    CardModel? parseCard(dynamic raw) {
      if (raw == null) return null;
      if (raw is Map<String, dynamic>) {
        if (raw.containsKey('card')) {
          return CardModel.fromJson(raw['card'] as Map<String, dynamic>);
        }
        return CardModel.fromJson(raw);
      }
      return null;
    }

    return QaydState(
      active: json['active'] as bool? ?? false,
      step: json['step'] != null ? QaydStep.fromValue(json['step'] as String) : null,
      reporter: json['reporter'] != null
          ? PlayerPosition.fromValue(json['reporter'] as String)
          : null,
      reporterIsBot: json['reporter_is_bot'] as bool?,
      menuOption: json['menu_option'] as String?,
      violationType: json['violation_type'] as String?,
      crimeCard: parseCard(json['crime_card']),
      proofCard: parseCard(json['proof_card']),
      verdict: json['verdict'] as String?,
      verdictMessage: json['verdict_message'] as String?,
      loserTeam: json['loser_team'] as String?,
      penaltyPoints: json['penalty_points'] as int?,
      timerDuration: json['timer_duration'] as int?,
      timerStart: json['timer_start'] as int?,
      reason: json['reason'] as String?,
      status: json['status'] as String?,
    );
  }
}

class TrickRecord {
  final List<dynamic> cards;
  final List<String>? playedBy;
  final String? winner;
  final int? points;
  final Map<String, dynamic>? metadata;

  const TrickRecord({
    this.cards = const [],
    this.playedBy,
    this.winner,
    this.points,
    this.metadata,
  });

  factory TrickRecord.fromJson(Map<String, dynamic> json) {
    return TrickRecord(
      cards: json['cards'] as List<dynamic>? ?? [],
      playedBy: (json['playedBy'] as List<dynamic>?)?.cast<String>(),
      winner: json['winner'] as String?,
      points: json['points'] as int?,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }
}

class TeamScores {
  final int us;
  final int them;

  const TeamScores({this.us = 0, this.them = 0});

  factory TeamScores.fromJson(Map<String, dynamic> json) {
    return TeamScores(
      us: json['us'] as int? ?? 0,
      them: json['them'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {'us': us, 'them': them};
}

class GameState {
  final String? gameId;
  final List<Player> players;
  final int currentTurnIndex;
  final GamePhase phase;
  final String? biddingPhase;
  final List<TableCard> tableCards;
  final GameMode? gameMode;
  final Suit? trumpSuit;
  final Bid bid;
  final TeamScores teamScores;
  final TeamScores matchScores;
  final List<RoundResult> roundHistory;
  final List<TrickRecord>? currentRoundTricks;
  final CardModel? floorCard;
  final List<CardModel> deck;
  final int dealerIndex;
  final int biddingRound;
  final Map<String, List<DeclaredProject>> declarations;
  final bool? isRoundTransitioning;
  final bool? isTrickTransitioning;
  final bool? isProjectRevealing;
  final int? trickCount;
  final DoublingLevel doublingLevel;
  final bool isLocked;
  final GameSettings settings;
  final SawaState? sawaState;
  final PlayerPosition? sawaClaimed;
  final bool? isFastForwarding;
  final QaydState? qaydState;
  final Map<String, dynamic>? akkaState;
  final Map<String, dynamic>? qaydPenalty;
  final Map<String, dynamic>? lastTrick;

  const GameState({
    this.gameId,
    this.players = const [],
    this.currentTurnIndex = 0,
    this.phase = GamePhase.waiting,
    this.biddingPhase,
    this.tableCards = const [],
    this.gameMode,
    this.trumpSuit,
    this.bid = const Bid.empty(),
    this.teamScores = const TeamScores(),
    this.matchScores = const TeamScores(),
    this.roundHistory = const [],
    this.currentRoundTricks,
    this.floorCard,
    this.deck = const [],
    this.dealerIndex = 0,
    this.biddingRound = 1,
    this.declarations = const {},
    this.isRoundTransitioning,
    this.isTrickTransitioning,
    this.isProjectRevealing,
    this.trickCount,
    this.doublingLevel = DoublingLevel.normal,
    this.isLocked = false,
    this.settings = const GameSettings(),
    this.sawaState,
    this.sawaClaimed,
    this.isFastForwarding,
    this.qaydState,
    this.akkaState,
    this.qaydPenalty,
    this.lastTrick,
  });

  /// Initial empty state
  factory GameState.initial() => const GameState();

  /// The current player (index 0 = bottom = human)
  Player? get currentPlayer =>
      players.isNotEmpty && currentTurnIndex < players.length
          ? players[currentTurnIndex]
          : null;

  /// My hand (always player index 0 after rotation)
  List<CardModel> get myHand =>
      players.isNotEmpty ? players[0].hand : [];

  /// Am I the current turn player?
  bool get isMyTurn => currentTurnIndex == 0;

  /// Is the game actively playing (bidding or playing)?
  bool get isActive =>
      phase == GamePhase.bidding ||
      phase == GamePhase.playing ||
      phase == GamePhase.doubling;

  GameState copyWith({
    String? gameId,
    List<Player>? players,
    int? currentTurnIndex,
    GamePhase? phase,
    String? biddingPhase,
    List<TableCard>? tableCards,
    GameMode? gameMode,
    Suit? trumpSuit,
    Bid? bid,
    TeamScores? teamScores,
    TeamScores? matchScores,
    List<RoundResult>? roundHistory,
    List<TrickRecord>? currentRoundTricks,
    CardModel? floorCard,
    List<CardModel>? deck,
    int? dealerIndex,
    int? biddingRound,
    Map<String, List<DeclaredProject>>? declarations,
    bool? isRoundTransitioning,
    bool? isTrickTransitioning,
    bool? isProjectRevealing,
    int? trickCount,
    DoublingLevel? doublingLevel,
    bool? isLocked,
    GameSettings? settings,
    SawaState? sawaState,
    PlayerPosition? sawaClaimed,
    bool? isFastForwarding,
    QaydState? qaydState,
    Map<String, dynamic>? akkaState,
    Map<String, dynamic>? qaydPenalty,
    Map<String, dynamic>? lastTrick,
  }) {
    return GameState(
      gameId: gameId ?? this.gameId,
      players: players ?? this.players,
      currentTurnIndex: currentTurnIndex ?? this.currentTurnIndex,
      phase: phase ?? this.phase,
      biddingPhase: biddingPhase ?? this.biddingPhase,
      tableCards: tableCards ?? this.tableCards,
      gameMode: gameMode ?? this.gameMode,
      trumpSuit: trumpSuit ?? this.trumpSuit,
      bid: bid ?? this.bid,
      teamScores: teamScores ?? this.teamScores,
      matchScores: matchScores ?? this.matchScores,
      roundHistory: roundHistory ?? this.roundHistory,
      currentRoundTricks: currentRoundTricks ?? this.currentRoundTricks,
      floorCard: floorCard ?? this.floorCard,
      deck: deck ?? this.deck,
      dealerIndex: dealerIndex ?? this.dealerIndex,
      biddingRound: biddingRound ?? this.biddingRound,
      declarations: declarations ?? this.declarations,
      isRoundTransitioning: isRoundTransitioning ?? this.isRoundTransitioning,
      isTrickTransitioning: isTrickTransitioning ?? this.isTrickTransitioning,
      isProjectRevealing: isProjectRevealing ?? this.isProjectRevealing,
      trickCount: trickCount ?? this.trickCount,
      doublingLevel: doublingLevel ?? this.doublingLevel,
      isLocked: isLocked ?? this.isLocked,
      settings: settings ?? this.settings,
      sawaState: sawaState ?? this.sawaState,
      sawaClaimed: sawaClaimed ?? this.sawaClaimed,
      isFastForwarding: isFastForwarding ?? this.isFastForwarding,
      qaydState: qaydState ?? this.qaydState,
      akkaState: akkaState ?? this.akkaState,
      qaydPenalty: qaydPenalty ?? this.qaydPenalty,
      lastTrick: lastTrick ?? this.lastTrick,
    );
  }

  factory GameState.fromJson(Map<String, dynamic> json) {
    return GameState(
      gameId: json['gameId'] as String? ?? json['roomId'] as String?,
      players: (json['players'] as List<dynamic>?)
              ?.map((p) => Player.fromJson(p as Map<String, dynamic>))
              .toList() ??
          [],
      currentTurnIndex: json['currentTurnIndex'] as int? ?? 0,
      phase: GamePhase.fromValue(json['phase'] as String? ?? 'WAITING'),
      biddingPhase: json['biddingPhase'] as String?,
      tableCards: (json['tableCards'] as List<dynamic>?)
              ?.map((tc) => TableCard.fromJson(tc as Map<String, dynamic>))
              .toList() ??
          [],
      gameMode: json['gameMode'] != null
          ? GameMode.fromValue(json['gameMode'] as String)
          : null,
      trumpSuit: json['trumpSuit'] != null
          ? Suit.fromSymbol(json['trumpSuit'] as String)
          : null,
      bid: json['bid'] != null
          ? Bid.fromJson(json['bid'] as Map<String, dynamic>)
          : const Bid.empty(),
      teamScores: json['teamScores'] != null
          ? TeamScores.fromJson(json['teamScores'] as Map<String, dynamic>)
          : const TeamScores(),
      matchScores: json['matchScores'] != null
          ? TeamScores.fromJson(json['matchScores'] as Map<String, dynamic>)
          : const TeamScores(),
      roundHistory: (json['roundHistory'] as List<dynamic>?)
              ?.map((r) => RoundResult.fromJson(r as Map<String, dynamic>))
              .toList() ??
          [],
      floorCard: json['floorCard'] != null
          ? CardModel.fromJson(json['floorCard'] as Map<String, dynamic>)
          : null,
      deck: (json['deck'] as List<dynamic>?)
              ?.map((c) => CardModel.fromJson(c as Map<String, dynamic>))
              .toList() ??
          [],
      dealerIndex: json['dealerIndex'] as int? ?? 0,
      biddingRound: json['biddingRound'] as int? ?? 1,
      declarations: _parseDeclarations(json['declarations']),
      doublingLevel: DoublingLevel.fromValue(json['doublingLevel'] as int? ?? 1),
      isLocked: json['isLocked'] as bool? ?? false,
      settings: json['settings'] != null
          ? GameSettings.fromJson(json['settings'] as Map<String, dynamic>)
          : const GameSettings(),
      sawaState: json['sawaState'] != null
          ? SawaState.fromJson(json['sawaState'] as Map<String, dynamic>)
          : null,
      qaydState: json['qaydState'] != null
          ? QaydState.fromJson(json['qaydState'] as Map<String, dynamic>)
          : null,
      trickCount: json['trickCount'] as int?,
      isRoundTransitioning: json['isRoundTransitioning'] as bool?,
      isTrickTransitioning: json['isTrickTransitioning'] as bool?,
      isFastForwarding: json['isFastForwarding'] as bool?,
    );
  }

  static Map<String, List<DeclaredProject>> _parseDeclarations(dynamic raw) {
    if (raw == null) return {};
    if (raw is! Map) return {};
    final result = <String, List<DeclaredProject>>{};
    for (final entry in (raw as Map<String, dynamic>).entries) {
      final projects = (entry.value as List<dynamic>?)
              ?.map((p) => DeclaredProject.fromJson(p as Map<String, dynamic>))
              .toList() ??
          [];
      result[entry.key] = projects;
    }
    return result;
  }
}
