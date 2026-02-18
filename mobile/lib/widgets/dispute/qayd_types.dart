/// qayd_types.dart — Shared types and constants for the Qayd dispute system.
///
/// Port of frontend/src/components/dispute/types.ts
library;
import 'dart:ui';

import '../../models/card_model.dart';

/// Menu options for the main Qayd menu.
enum MainMenuOption {
  revealCards('REVEAL_CARDS'),
  wrongSawa('WRONG_SAWA'),
  wrongAkka('WRONG_AKKA');

  final String value;
  const MainMenuOption(this.value);
}

/// Specific violation types for card-level disputes.
enum ViolationType {
  revoke('REVOKE'),
  trumpInDouble('TRUMP_IN_DOUBLE'),
  noOvertrump('NO_OVERTRUMP'),
  noTrump('NO_TRUMP');

  final String value;
  const ViolationType(this.value);
}

/// A card selected as crime or proof evidence.
class CardSelection {
  final CardModel card;
  final int trickIdx;
  final int cardIdx;
  final String playedBy;

  const CardSelection({
    required this.card,
    required this.trickIdx,
    required this.cardIdx,
    required this.playedBy,
  });
}

/// Verdict result after adjudication.
class VerdictData {
  final bool isCorrect;
  final String message;
  final String reason;
  final int penalty;
  final String? loserTeam;

  const VerdictData({
    required this.isCorrect,
    required this.message,
    required this.reason,
    required this.penalty,
    this.loserTeam,
  });
}

/// Menu option display data.
class MenuOptionData {
  final MainMenuOption key;
  final String ar;
  final String icon;
  const MenuOptionData({
    required this.key,
    required this.ar,
    required this.icon,
  });
}

const mainMenuOptions = [
  MenuOptionData(key: MainMenuOption.revealCards, ar: 'كشف الأوراق', icon: '🃏'),
  MenuOptionData(key: MainMenuOption.wrongSawa, ar: 'سوا خاطئ', icon: '🤝'),
  MenuOptionData(key: MainMenuOption.wrongAkka, ar: 'أكة خاطئة', icon: '👑'),
];

/// Violation type display data.
class ViolationData {
  final ViolationType key;
  final String ar;
  const ViolationData({required this.key, required this.ar});
}

const violationTypesHokum = [
  ViolationData(key: ViolationType.revoke, ar: 'قاطع'),
  ViolationData(key: ViolationType.trumpInDouble, ar: 'ربع في الدبل'),
  ViolationData(key: ViolationType.noOvertrump, ar: 'ما كبر بحكم'),
  ViolationData(key: ViolationType.noTrump, ar: 'ما دق بحكم'),
];

const violationTypesSun = [
  ViolationData(key: ViolationType.revoke, ar: 'قاطع'),
];

// Qayd UI colors
const qaydBgDark = Color(0xFF404040);
const qaydBgDarker = Color(0xFF333333);
const qaydBorder = Color(0xFF555555);
const qaydCrimeColor = Color(0xFFEC4899); // Pink-500
const qaydProofColor = Color(0xFF22C55E); // Green-500
