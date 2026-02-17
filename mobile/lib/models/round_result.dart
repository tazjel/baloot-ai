// RoundResult, DetailedScore, ScoreBreakdown — Scoring models.
import 'declared_project.dart';

class DetailedScore {
  final int aklat;
  final int ardh;
  final int mashaari;
  final int abnat;
  final int result;
  final List<DeclaredProject> projects;
  final int? rawCardPoints;
  final int? projectPoints;
  final int? totalRaw;
  final int? gamePoints;

  const DetailedScore({
    this.aklat = 0,
    this.ardh = 0,
    this.mashaari = 0,
    this.abnat = 0,
    this.result = 0,
    this.projects = const [],
    this.rawCardPoints,
    this.projectPoints,
    this.totalRaw,
    this.gamePoints,
  });

  factory DetailedScore.fromJson(Map<String, dynamic> json) {
    return DetailedScore(
      aklat: json['aklat'] as int? ?? 0,
      ardh: json['ardh'] as int? ?? 0,
      mashaari: json['mashaari'] as int? ?? 0,
      abnat: json['abnat'] as int? ?? 0,
      result: json['result'] as int? ?? 0,
      projects: (json['projects'] as List<dynamic>?)
              ?.map((p) => DeclaredProject.fromJson(p as Map<String, dynamic>))
              .toList() ??
          [],
      rawCardPoints: json['rawCardPoints'] as int?,
      projectPoints: json['projectPoints'] as int?,
      totalRaw: json['totalRaw'] as int?,
      gamePoints: json['gamePoints'] as int?,
    );
  }

  Map<String, dynamic> toJson() => {
        'aklat': aklat,
        'ardh': ardh,
        'mashaari': mashaari,
        'abnat': abnat,
        'result': result,
        'projects': projects.map((p) => p.toJson()).toList(),
        if (rawCardPoints != null) 'rawCardPoints': rawCardPoints,
        if (projectPoints != null) 'projectPoints': projectPoints,
        if (totalRaw != null) 'totalRaw': totalRaw,
        if (gamePoints != null) 'gamePoints': gamePoints,
      };
}

class ScoreBreakdown {
  final int rawCardPoints;
  final int projectPoints;
  final int totalRaw;
  final int gamePoints;
  final bool isKaboot;
  final int multiplierApplied;

  const ScoreBreakdown({
    this.rawCardPoints = 0,
    this.projectPoints = 0,
    this.totalRaw = 0,
    this.gamePoints = 0,
    this.isKaboot = false,
    this.multiplierApplied = 1,
  });
}

class RoundResult {
  final int? roundNumber;
  final DetailedScore us;
  final DetailedScore them;
  final String winner; // 'us' | 'them' | 'tie' | 'NONE'
  final String? bidder;
  final String? gameMode; // 'SUN' | 'HOKUM'
  final int? doubling;
  final String? reason;

  const RoundResult({
    this.roundNumber,
    required this.us,
    required this.them,
    required this.winner,
    this.bidder,
    this.gameMode,
    this.doubling,
    this.reason,
  });

  factory RoundResult.fromJson(Map<String, dynamic> json) {
    return RoundResult(
      roundNumber: json['roundNumber'] as int?,
      us: DetailedScore.fromJson(json['us'] as Map<String, dynamic>),
      them: DetailedScore.fromJson(json['them'] as Map<String, dynamic>),
      winner: json['winner'] as String? ?? 'NONE',
      bidder: json['bidder'] as String?,
      gameMode: json['gameMode'] as String?,
      doubling: json['doubling'] as int?,
      reason: json['reason'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        if (roundNumber != null) 'roundNumber': roundNumber,
        'us': us.toJson(),
        'them': them.toJson(),
        'winner': winner,
        if (bidder != null) 'bidder': bidder,
        if (gameMode != null) 'gameMode': gameMode,
        if (doubling != null) 'doubling': doubling,
        if (reason != null) 'reason': reason,
      };
}
