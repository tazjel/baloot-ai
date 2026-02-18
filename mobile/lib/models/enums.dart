/// Baloot AI — All game enumerations.
///
/// Direct port from frontend/src/types.ts enums.
library;

// Card Suits — using Unicode symbols matching backend
enum Suit {
  hearts('♥'),
  diamonds('♦'),
  clubs('♣'),
  spades('♠');

  final String symbol;
  const Suit(this.symbol);

  /// Parse from string symbol (♥, ♦, ♣, ♠)
  static Suit fromSymbol(String s) {
    return Suit.values.firstWhere(
      (suit) => suit.symbol == s,
      orElse: () => throw ArgumentError('Unknown suit symbol: $s'),
    );
  }

  /// Parse from JSON string
  factory Suit.fromJson(String json) => fromSymbol(json);
  String toJson() => symbol;

  bool get isRed => this == Suit.hearts || this == Suit.diamonds;
  bool get isBlack => this == Suit.spades || this == Suit.clubs;
}

// Card Ranks
enum Rank {
  seven('7'),
  eight('8'),
  nine('9'),
  ten('10'),
  jack('J'),
  queen('Q'),
  king('K'),
  ace('A');

  final String symbol;
  const Rank(this.symbol);

  static Rank fromSymbol(String s) {
    return Rank.values.firstWhere(
      (r) => r.symbol == s,
      orElse: () => throw ArgumentError('Unknown rank symbol: $s'),
    );
  }

  factory Rank.fromJson(String json) => fromSymbol(json);
  String toJson() => symbol;
}

// Game Phase
enum GamePhase {
  waiting('WAITING'),
  bidding('BIDDING'),
  doubling('DOUBLING'),
  variantSelection('VARIANT_SELECTION'),
  playing('PLAYING'),
  gameOver('GAMEOVER');

  final String value;
  const GamePhase(this.value);

  static GamePhase fromValue(String v) {
    return GamePhase.values.firstWhere(
      (p) => p.value == v,
      orElse: () => GamePhase.waiting,
    );
  }

  factory GamePhase.fromJson(String json) => fromValue(json);
  String toJson() => value;
}

// Player Position (relative to screen)
enum PlayerPosition {
  bottom('Bottom'),
  right('Right'),
  top('Top'),
  left('Left');

  final String value;
  const PlayerPosition(this.value);

  static PlayerPosition fromValue(String v) {
    return PlayerPosition.values.firstWhere(
      (p) => p.value == v,
      orElse: () => PlayerPosition.bottom,
    );
  }

  factory PlayerPosition.fromJson(String json) => fromValue(json);
  String toJson() => value;
}

// Project types (Mashaari)
enum ProjectType {
  sira('SIRA'),
  fifty('FIFTY'),
  hundred('HUNDRED'),
  fourHundred('FOUR_HUNDRED'),
  baloot('BALOOT');

  final String value;
  const ProjectType(this.value);

  static ProjectType fromValue(String v) {
    return ProjectType.values.firstWhere(
      (p) => p.value == v,
      orElse: () => ProjectType.sira,
    );
  }

  factory ProjectType.fromJson(String json) => fromValue(json);
  String toJson() => value;
}

// Doubling levels
enum DoublingLevel {
  normal(1),
  double_(2),
  triple(3),
  quadruple(4),
  gahwa(100);

  final int value;
  const DoublingLevel(this.value);

  static DoublingLevel fromValue(int v) {
    return DoublingLevel.values.firstWhere(
      (d) => d.value == v,
      orElse: () => DoublingLevel.normal,
    );
  }
}

// Bot difficulty levels
enum BotDifficulty {
  easy('EASY'),
  medium('MEDIUM'),
  hard('HARD'),
  khalid('KHALID');

  final String value;
  const BotDifficulty(this.value);

  static BotDifficulty fromValue(String v) {
    return BotDifficulty.values.firstWhere(
      (d) => d.value == v,
      orElse: () => BotDifficulty.hard,
    );
  }
}

// League tiers
enum LeagueTier {
  bronze('Bronze', 0),
  silver('Silver', 1200),
  gold('Gold', 1400),
  platinum('Platinum', 1600),
  diamond('Diamond', 1800),
  grandmaster('Grandmaster', 2000);

  final String label;
  final int minPoints;
  const LeagueTier(this.label, this.minPoints);

  static LeagueTier fromPoints(int points) {
    final tiers = LeagueTier.values.reversed;
    for (final tier in tiers) {
      if (points >= tier.minPoints) return tier;
    }
    return LeagueTier.bronze;
  }

  static LeagueTier fromLabel(String label) {
    return LeagueTier.values.firstWhere(
      (t) => t.label.toLowerCase() == label.toLowerCase(),
      orElse: () => LeagueTier.bronze,
    );
  }
}

// Game mode
enum GameMode {
  sun('SUN'),
  hokum('HOKUM');

  final String value;
  const GameMode(this.value);

  static GameMode fromValue(String v) {
    return GameMode.values.firstWhere(
      (m) => m.value == v,
      orElse: () => GameMode.sun,
    );
  }
}

// Qayd (dispute) steps
enum QaydStep {
  idle('IDLE'),
  mainMenu('MAIN_MENU'),
  violationSelect('VIOLATION_SELECT'),
  selectCard1('SELECT_CARD_1'),
  selectCard2('SELECT_CARD_2'),
  adjudication('ADJUDICATION'),
  result('RESULT');

  final String value;
  const QaydStep(this.value);

  static QaydStep fromValue(String v) {
    return QaydStep.values.firstWhere(
      (s) => s.value == v,
      orElse: () => QaydStep.idle,
    );
  }
}

// Theme mode
enum AppThemeMode {
  auto,
  light,
  dark,
}

// Sawa status
enum SawaStatus {
  pending('PENDING'),
  accepted('ACCEPTED'),
  refused('REFUSED'),
  none('NONE');

  final String value;
  const SawaStatus(this.value);

  static SawaStatus fromValue(String v) {
    return SawaStatus.values.firstWhere(
      (s) => s.value == v,
      orElse: () => SawaStatus.none,
    );
  }
}
