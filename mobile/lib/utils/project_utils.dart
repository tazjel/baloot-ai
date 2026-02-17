/// projectUtils.dart — Project detection, comparison, and conflict resolution.
///
/// Port of frontend/src/utils/projectUtils.ts
import '../models/card_model.dart';
import '../models/declared_project.dart';
import '../models/enums.dart';
import '../core/constants.dart';

/// Get project score value
int getProjectScoreValue(ProjectType type, GameMode mode) {
  final modeKey = mode == GameMode.sun ? 'SUN' : 'HOKUM';
  return projectScores[modeKey]?[type] ?? 0;
}

/// Compare two projects. Returns positive if p1 > p2.
int compareProjects(DeclaredProject p1, DeclaredProject p2, [GameMode mode = GameMode.hokum]) {
  final val1 = getProjectScoreValue(p1.type, mode);
  final val2 = getProjectScoreValue(p2.type, mode);
  if (val1 != val2) return val1 - val2;

  final r1 = sequenceOrder.indexOf(p1.rank);
  final r2 = sequenceOrder.indexOf(p2.rank);
  return r2 - r1;
}

/// Detect all projects in a hand.
List<DeclaredProject> detectProjects(
  List<CardModel> hand,
  PlayerPosition playerPos, [
  Suit? trumpSuit,
]) {
  final projects = <DeclaredProject>[];

  // Group cards by suit
  final bySuit = <Suit, List<CardModel>>{};
  for (final suit in Suit.values) {
    bySuit[suit] = [];
  }
  for (final card in hand) {
    bySuit[card.suit]!.add(card);
  }

  // Count ranks
  final rankCounts = <Rank, int>{};
  for (final card in hand) {
    rankCounts[card.rank] = (rankCounts[card.rank] ?? 0) + 1;
  }

  // 400 (4 Aces)
  if (rankCounts[Rank.ace] == 4) {
    projects.add(DeclaredProject(
      type: ProjectType.fourHundred,
      rank: Rank.ace,
      suit: Suit.spades,
      owner: playerPos,
    ));
  }

  // 100 (4 of K, Q, J, 10)
  for (final rank in [Rank.king, Rank.queen, Rank.jack, Rank.ten]) {
    if (rankCounts[rank] == 4) {
      projects.add(DeclaredProject(
        type: ProjectType.hundred,
        rank: rank,
        suit: Suit.spades,
        owner: playerPos,
      ));
    }
  }

  // Sequences (Sira, 50, 100)
  for (final suit in Suit.values) {
    final cards = bySuit[suit]!;
    if (cards.length < 3) continue;
    cards.sort((a, b) =>
        sequenceOrder.indexOf(a.rank) - sequenceOrder.indexOf(b.rank));

    var currentSeq = [cards[0]];
    for (int i = 1; i < cards.length; i++) {
      final prevIdx = sequenceOrder.indexOf(currentSeq.last.rank);
      final currIdx = sequenceOrder.indexOf(cards[i].rank);
      if (currIdx == prevIdx + 1) {
        currentSeq.add(cards[i]);
      } else {
        _processSequence(currentSeq, projects, playerPos, suit);
        currentSeq = [cards[i]];
      }
    }
    _processSequence(currentSeq, projects, playerPos, suit);
  }

  // Baloot (K + Q of Trump)
  if (trumpSuit != null) {
    final hasKing = hand.any((c) => c.suit == trumpSuit && c.rank == Rank.king);
    final hasQueen = hand.any((c) => c.suit == trumpSuit && c.rank == Rank.queen);
    if (hasKing && hasQueen) {
      projects.add(DeclaredProject(
        type: ProjectType.baloot,
        rank: Rank.king,
        suit: trumpSuit,
        owner: playerPos,
      ));
    }
  }

  return projects;
}

void _processSequence(
  List<CardModel> seq,
  List<DeclaredProject> projects,
  PlayerPosition pos,
  Suit suit,
) {
  if (seq.length >= 5) {
    projects.add(DeclaredProject(type: ProjectType.hundred, rank: seq[0].rank, suit: suit, owner: pos));
  } else if (seq.length == 4) {
    projects.add(DeclaredProject(type: ProjectType.fifty, rank: seq[0].rank, suit: suit, owner: pos));
  } else if (seq.length == 3) {
    projects.add(DeclaredProject(type: ProjectType.sira, rank: seq[0].rank, suit: suit, owner: pos));
  }
}

/// Resolve project conflicts between teams.
Map<String, List<DeclaredProject>> resolveProjectConflicts(
  Map<String, List<DeclaredProject>> declarations,
  GameMode mode,
) {
  final resolved = <String, List<DeclaredProject>>{};
  final mashaari = <String, List<DeclaredProject>>{'us': [], 'them': []};

  for (final pos in declarations.keys) {
    resolved[pos] = [];
  }

  for (final entry in declarations.entries) {
    final pos = entry.key;
    final isUs = pos == PlayerPosition.bottom.value || pos == PlayerPosition.top.value;
    for (final p in entry.value) {
      if (p.type == ProjectType.baloot) {
        resolved[pos]!.add(p);
      } else {
        if (isUs) {
          mashaari['us']!.add(p);
        } else {
          mashaari['them']!.add(p);
        }
      }
    }
  }

  mashaari['us']!.sort((a, b) => compareProjects(b, a, mode));
  mashaari['them']!.sort((a, b) => compareProjects(b, a, mode));

  final bestUs = mashaari['us']!.isNotEmpty ? mashaari['us']!.first : null;
  final bestThem = mashaari['them']!.isNotEmpty ? mashaari['them']!.first : null;

  String winningTeam = 'none';
  if (bestUs != null && bestThem == null) {
    winningTeam = 'us';
  } else if (bestUs == null && bestThem != null) {
    winningTeam = 'them';
  } else if (bestUs != null && bestThem != null) {
    final diff = compareProjects(bestUs, bestThem, mode);
    if (diff > 0) {
      winningTeam = 'us';
    } else if (diff < 0) {
      winningTeam = 'them';
    }
  }

  if (winningTeam == 'us') {
    for (final entry in declarations.entries) {
      final pos = entry.key;
      if (pos == PlayerPosition.bottom.value || pos == PlayerPosition.top.value) {
        for (final p in entry.value) {
          if (p.type != ProjectType.baloot) resolved[pos]!.add(p);
        }
      }
    }
  } else if (winningTeam == 'them') {
    for (final entry in declarations.entries) {
      final pos = entry.key;
      if (pos == PlayerPosition.right.value || pos == PlayerPosition.left.value) {
        for (final p in entry.value) {
          if (p.type != ProjectType.baloot) resolved[pos]!.add(p);
        }
      }
    }
  }

  return resolved;
}
