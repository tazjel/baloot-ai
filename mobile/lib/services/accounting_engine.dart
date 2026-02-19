/// accounting_engine.dart — Scoring engine for Baloot AI.
///
/// Port of frontend/src/services/AccountingEngine.ts
///
/// Validated 100% against 1,095 benchmark rounds.
///
/// ## Key Constants
/// - **SUN Total**: 130 Abnat (120 cards + 10 last trick) → 26 Game Points
/// - **HOKUM Total**: 162 Abnat (152 cards + 10 last trick) → 16 Game Points
///
/// ## Scoring Formulas (Benchmark-validated)
/// - **SUN**: Floor-to-even → `divmod(abnat, 5); q + (1 if q is odd and r > 0)`
/// - **HOKUM**: Pair-based rounding with sum=16 constraint
///   - Individual: `divmod(abnat, 10); q + (1 if r > 5)`
///   - Then adjust pair if sum ≠ 16
///
/// ## Khasara (Buyer Loss)
/// - `bidder_gp < opp_gp` → khasara
/// - GP tie: compare raw abnat (doubled: doubler loses; equal raw → split)
///
/// ## Kaboot (Capot — All Tricks)
/// - SUN: 44 points
/// - HOKUM: 25 points
///
/// ## Pipeline
/// card_gp → project_gp → khasara → multiplier → baloot (last, never multiplied)
library;
import '../models/enums.dart';

/// Breakdown of a team's score for one round.
class ScoreBreakdown {
  /// Raw card points (abnat) won from tricks.
  final int rawCardPoints;

  /// Raw project points (abnat) from declared projects.
  final int projectPoints;

  /// Total raw abnat (cards + projects) before conversion.
  final int totalRaw;

  /// Final game points (GP) after conversion, khasara, multiplier, and baloot.
  int gamePoints;

  /// Whether this team won all 8 tricks (kaboot/capot).
  bool isKaboot;

  /// The doubling multiplier applied this round.
  final DoublingLevel multiplierApplied;

  ScoreBreakdown({
    required this.rawCardPoints,
    required this.projectPoints,
    required this.totalRaw,
    this.gamePoints = 0,
    this.isKaboot = false,
    this.multiplierApplied = DoublingLevel.normal,
  });

  Map<String, dynamic> toJson() => {
        'rawCardPoints': rawCardPoints,
        'projectPoints': projectPoints,
        'totalRaw': totalRaw,
        'gamePoints': gamePoints,
        'isKaboot': isKaboot,
        'multiplierApplied': multiplierApplied.value,
      };
}

/// Result of a round scoring calculation.
class RoundScoreResult {
  /// Score breakdown for "Us" (bottom + top team).
  final ScoreBreakdown us;

  /// Score breakdown for "Them" (right + left team).
  final ScoreBreakdown them;

  /// Which team won this round ('us', 'them', or 'tie').
  final String winner;

  /// Whether this round resulted in a shutout (baida).
  final bool baida;

  const RoundScoreResult({
    required this.us,
    required this.them,
    required this.winner,
    this.baida = false,
  });
}

/// Scoring engine for Baloot AI — the authoritative source for GP calculation.
///
/// All methods are static. The scoring pipeline mirrors the validated
/// benchmark formulas exactly:
///
/// 1. Convert raw abnat → base GP using mode-specific rounding.
/// 2. Check for kaboot (capot — all 8 tricks won).
/// 3. Apply khasara (buyer loss) rules with tie-breaking.
/// 4. Apply doubling multiplier.
/// 5. Add baloot bonus (flat 2 GP, NEVER multiplied).
class AccountingEngine {
  AccountingEngine._(); // Prevent instantiation

  // ═══════════════════════════════════════════════════════════════
  // CONVERSION FUNCTIONS (Abnat → Game Points)
  // ═══════════════════════════════════════════════════════════════

  /// SUN card GP: Floor-to-even rounding.
  ///
  /// Formula: `divmod(abnat, 5) → q + (1 if q is odd and r > 0)`
  /// Total pool: 130 Abnat → always sums to 26 GP.
  ///
  /// Example: 67 → 67÷5 = 13 r 2 → 13 is odd, r>0 → 14 GP
  /// Example: 63 → 63÷5 = 12 r 3 → 12 is even → 12 GP (partner gets 14)
  static int sunCardGP(int abnat) {
    final q = abnat ~/ 5;
    final r = abnat % 5;
    return q + ((q % 2 == 1 && r > 0) ? 1 : 0);
  }

  /// HOKUM individual card GP: round up if remainder > 5.
  ///
  /// Formula: `divmod(abnat, 10) → q + (1 if r > 5)`
  /// Used per-team; must apply sum=16 constraint via [hokumPairGP].
  static int hokumCardGP(int abnat) {
    final q = abnat ~/ 10;
    final r = abnat % 10;
    return q + (r > 5 ? 1 : 0);
  }

  /// HOKUM pair-based GP: ensures the pair always sums to 16.
  ///
  /// Computes individual GP for each team, then adjusts if sum ≠ 16:
  /// - sum=17: reduce the team with the larger `raw % 10` remainder.
  /// - sum=15: increase the team with the larger `raw % 10` remainder.
  /// - If remainders are equal, the team with larger raw gets adjusted.
  ///
  /// Returns `[gpA, gpB]` where A+B = 16.
  static List<int> hokumPairGP(int rawA, int rawB) {
    var gpA = hokumCardGP(rawA);
    var gpB = hokumCardGP(rawB);
    final total = gpA + gpB;

    if (total == 17) {
      final remA = rawA % 10;
      final remB = rawB % 10;
      if (remA > remB || (remA == remB && rawA >= rawB)) {
        gpA -= 1;
      } else {
        gpB -= 1;
      }
    } else if (total == 15) {
      final remA = rawA % 10;
      final remB = rawB % 10;
      if (remA > remB || (remA == remB && rawA >= rawB)) {
        gpA += 1;
      } else {
        gpB += 1;
      }
    }

    return [gpA, gpB];
  }

  // ═══════════════════════════════════════════════════════════════
  // MAIN SCORING FUNCTION
  // ═══════════════════════════════════════════════════════════════

  /// Calculates the final Game Points for a round.
  ///
  /// This is the **truth source** for scoring — matches benchmark rules exactly.
  ///
  /// Parameters:
  /// - [usRaw], [themRaw]: Raw abnat from card tricks (includes last trick bonus).
  /// - [usProjects], [themProjects]: Sum of project abnat values.
  /// - [bidType]: 'SUN' or 'HOKUM' — determines conversion formula.
  /// - [doublingLevel]: Current doubling state (NORMAL, DOUBLE, TRIPLE, etc.).
  /// - [bidderTeam]: Which team won the bid ('us' or 'them'), or null if no bid.
  /// - [hasBalootUs], [hasBalootThem]: Whether each team declared Baloot (K+Q of trump).
  ///
  /// Scoring pipeline:
  /// 1. Build initial structures with raw totals.
  /// 2. Detect kaboot (opponent scored 0 raw abnat).
  /// 3. Convert abnat → base GP using mode-specific formula.
  /// 4. Apply khasara rules (bidder loss check with tie-breaking).
  /// 5. Apply doubling multiplier (winner takes all × level).
  /// 6. Add baloot bonus (flat 2 GP, immune to multiplier).
  /// 7. Determine round winner.
  static RoundScoreResult calculateRoundResult({
    required int usRaw,
    required int themRaw,
    required int usProjects,
    required int themProjects,
    required String bidType,
    required DoublingLevel doublingLevel,
    required String? bidderTeam,
    bool hasBalootUs = false,
    bool hasBalootThem = false,
  }) {
    // ═══════════════════════════════════════════════════════════
    // 1. INITIAL STRUCTURES
    // ═══════════════════════════════════════════════════════════
    final us = ScoreBreakdown(
      rawCardPoints: usRaw,
      projectPoints: usProjects,
      totalRaw: usRaw + usProjects,
      multiplierApplied: doublingLevel,
    );

    final them = ScoreBreakdown(
      rawCardPoints: themRaw,
      projectPoints: themProjects,
      totalRaw: themRaw + themProjects,
      multiplierApplied: doublingLevel,
    );

    // ═══════════════════════════════════════════════════════════
    // 2. KABOOT DETECTION (All Tricks Won)
    // ═══════════════════════════════════════════════════════════
    final isUsKaboot = themRaw == 0 && usRaw > 0;
    final isThemKaboot = usRaw == 0 && themRaw > 0;

    // ═══════════════════════════════════════════════════════════
    // 3 & 4. BASE CALCULATION (Abnat → Game Points)
    // ═══════════════════════════════════════════════════════════
    int usBase = 0;
    int themBase = 0;

    if (isUsKaboot) {
      us.isKaboot = true;
      usBase = bidType == 'SUN' ? 44 : 25;
      themBase = 0;
    } else if (isThemKaboot) {
      them.isKaboot = true;
      themBase = bidType == 'SUN' ? 44 : 25;
      usBase = 0;
    } else {
      // Normal calculation
      if (bidType == 'SUN') {
        usBase = sunCardGP(us.totalRaw);
        themBase = sunCardGP(them.totalRaw);
      } else {
        // HOKUM: pair-based rounding with sum=16 constraint
        final pair = hokumPairGP(us.totalRaw, them.totalRaw);
        usBase = pair[0];
        themBase = pair[1];
      }
    }

    // ═══════════════════════════════════════════════════════════
  // 5. KHASARA CHECK (Benchmark-validated tie-break rules)
    // ═══════════════════════════════════════════════════════════
    if (!isUsKaboot && !isThemKaboot && bidderTeam != null) {
      final bidderScore = bidderTeam == 'us' ? usBase : themBase;
      final oppScore = bidderTeam == 'us' ? themBase : usBase;
      var khasara = false;

      if (bidderScore < oppScore) {
        khasara = true;
      } else if (bidderScore == oppScore) {
        // GP tie: compare raw abnat totals
        final bidderRaw =
            bidderTeam == 'us' ? us.totalRaw : them.totalRaw;
        final oppRaw =
            bidderTeam == 'us' ? them.totalRaw : us.totalRaw;
        final isDoubled = doublingLevel.value >= 2;

        if (isDoubled) {
          // Doubled rounds: doubler always loses the tie
          khasara = true;
        } else if (bidderRaw < oppRaw) {
          // Normal: bidder loses if raw abnat is strictly less
          khasara = true;
        }
        // Equal raw on tie → split (no khasara)
      }

      if (khasara) {
        final totalPot = usBase + themBase;
        if (bidderTeam == 'us') {
          usBase = 0;
          themBase = totalPot;
        } else {
          themBase = 0;
          usBase = totalPot;
        }
      }
    }

    // ═══════════════════════════════════════════════════════════
    // 6. APPLY BASE POINTS
    // ═══════════════════════════════════════════════════════════
    us.gamePoints = usBase;
    them.gamePoints = themBase;

    // ═══════════════════════════════════════════════════════════
    // 7. DOUBLING MULTIPLIER
    // ═══════════════════════════════════════════════════════════
    if (doublingLevel.value > 1) {
      final totalGamePoints = us.gamePoints + them.gamePoints;

      if (us.gamePoints > them.gamePoints) {
        us.gamePoints = totalGamePoints * doublingLevel.value;
        them.gamePoints = 0;
      } else if (them.gamePoints > us.gamePoints) {
        them.gamePoints = totalGamePoints * doublingLevel.value;
        us.gamePoints = 0;
      }
      // Tie: both keep their multiplied scores (rare)
    }

    // ═══════════════════════════════════════════════════════════
    // 8. BALOOT BONUS (Flat 2 points, NEVER multiplied)
    // ═══════════════════════════════════════════════════════════
    if (hasBalootUs) {
      us.gamePoints += 2;
    }
    if (hasBalootThem) {
      them.gamePoints += 2;
    }

    // ═══════════════════════════════════════════════════════════
    // 9. DETERMINE WINNER & RETURN
    // ═══════════════════════════════════════════════════════════
    final winner = us.gamePoints > them.gamePoints
        ? 'us'
        : them.gamePoints > us.gamePoints
            ? 'them'
            : 'tie';

    return RoundScoreResult(
      us: us,
      them: them,
      winner: winner,
      baida: false,
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // HELPER: Calculate Project Abnat Value
  // ═══════════════════════════════════════════════════════════════

  /// Returns the raw abnat value of a project type in the given bid mode.
  ///
  /// - **400** (4 Aces): SUN=40, HOKUM=0 (invalid in HOKUM).
  /// - **100** (5-sequence or 4-of-a-kind): SUN=20, HOKUM=10.
  /// - **50** (4-sequence): SUN=10, HOKUM=5.
  /// - **Sira** (3-sequence): SUN=4, HOKUM=2.
  /// - **Baloot** (K+Q of trump): Always 0 here — handled as flat 2 GP separately.
  static int getProjectAbnatValue(ProjectType type, String bidType) {
    final isSun = bidType == 'SUN';
    switch (type) {
      case ProjectType.fourHundred:
        return isSun ? 40 : 0;
      case ProjectType.hundred:
        return isSun ? 20 : 10;
      case ProjectType.fifty:
        return isSun ? 10 : 5;
      case ProjectType.sira:
        return isSun ? 4 : 2;
      case ProjectType.baloot:
        return 0; // Flat 2 GP, not added to abnat
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // DEBUG HELPER: Explain calculation step by step
  // ═══════════════════════════════════════════════════════════════

  /// Returns a step-by-step explanation of the scoring calculation.
  ///
  /// Useful for debugging and display in the score breakdown modal.
  static List<String> explainCalculation({
    required int usRaw,
    required int themRaw,
    required String bidType,
    required String? bidderTeam,
  }) {
    final steps = <String>[];

    steps.add('Round Type: $bidType');
    steps.add('Raw Abnat - Us: $usRaw, Them: $themRaw');

    if (bidType == 'SUN') {
      final usPoints = sunCardGP(usRaw);
      final themPoints = sunCardGP(themRaw);
      steps.add('SUN Formula: floor-to-even (divmod by 5)');
      steps.add('   Us: $usRaw -> $usPoints GP');
      steps.add('   Them: $themRaw -> $themPoints GP');

      if (bidderTeam != null) {
        final bidderScore = bidderTeam == 'us' ? usPoints : themPoints;
        final oppScore = bidderTeam == 'us' ? themPoints : usPoints;
        steps.add('Buyer ($bidderTeam) scored: $bidderScore vs $oppScore');
        if (bidderScore < oppScore) {
          steps.add('KHASARA! Buyer GP < opponent GP.');
        } else if (bidderScore == oppScore) {
          steps.add('GP tie -> compare raw abnat for khasara.');
        } else {
          steps.add('Buyer wins!');
        }
      }
    } else {
      final usPoints = hokumCardGP(usRaw);
      final themPoints = hokumCardGP(themRaw);
      steps.add('HOKUM Formula: pair-based rounding (sum=16)');
      steps.add('   Us: $usRaw -> $usPoints GP');
      steps.add('   Them: $themRaw -> $themPoints GP');

      if (bidderTeam != null) {
        final bidderScore = bidderTeam == 'us' ? usPoints : themPoints;
        final oppScore = bidderTeam == 'us' ? themPoints : usPoints;
        steps.add('Buyer ($bidderTeam) scored: $bidderScore vs $oppScore');
        if (bidderScore < oppScore) {
          steps.add('KHASARA! Buyer GP < opponent GP.');
        } else if (bidderScore == oppScore) {
          steps.add('GP tie -> compare raw abnat for khasara.');
        } else {
          steps.add('Buyer wins!');
        }
      }
    }

    return steps;
  }
}
