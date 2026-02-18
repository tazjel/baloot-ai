/// Baloot AI — Game constants.
///
/// Port of frontend/src/constants.ts
library;
import '../models/enums.dart';

/// Rank order for sequences (A, K, Q, J, 10, 9, 8, 7)
const List<Rank> sequenceOrder = [
  Rank.ace, Rank.king, Rank.queen, Rank.jack,
  Rank.ten, Rank.nine, Rank.eight, Rank.seven,
];

/// Strength order for trick resolution
const Map<String, List<Rank>> strengthOrder = {
  'SUN': [Rank.seven, Rank.eight, Rank.nine, Rank.jack, Rank.queen, Rank.king, Rank.ten, Rank.ace],
  'HOKUM_TRUMP': [Rank.seven, Rank.eight, Rank.queen, Rank.king, Rank.ten, Rank.ace, Rank.nine, Rank.jack],
  'HOKUM_NORMAL': [Rank.seven, Rank.eight, Rank.nine, Rank.jack, Rank.queen, Rank.king, Rank.ten, Rank.ace],
};

/// Point values for scoring (abnat)
const Map<String, Map<Rank, int>> pointValues = {
  'SUN': {
    Rank.ace: 11, Rank.ten: 10, Rank.king: 4, Rank.queen: 3,
    Rank.jack: 2, Rank.nine: 0, Rank.eight: 0, Rank.seven: 0,
  },
  'HOKUM': {
    Rank.jack: 20, Rank.nine: 14, Rank.ace: 11, Rank.ten: 10,
    Rank.king: 4, Rank.queen: 3, Rank.eight: 0, Rank.seven: 0,
  },
};

/// Project score values by mode
const Map<String, Map<ProjectType, int>> projectScores = {
  'SUN': {
    ProjectType.fourHundred: 400,
    ProjectType.hundred: 200,
    ProjectType.fifty: 100,
    ProjectType.sira: 40,
    ProjectType.baloot: 0,
  },
  'HOKUM': {
    ProjectType.fourHundred: 0,
    ProjectType.hundred: 100,
    ProjectType.fifty: 50,
    ProjectType.sira: 20,
    ProjectType.baloot: 20,
  },
};

/// Avatar URLs
const Map<String, String> avatars = {
  'ME': 'https://picsum.photos/id/64/100/100',
  'RIGHT': 'https://picsum.photos/id/65/100/100',
  'TOP': 'https://picsum.photos/id/66/100/100',
  'LEFT': 'https://picsum.photos/id/67/100/100',
};

/// Bot player defaults
class BotConfig {
  final PlayerPosition position;
  final String name;
  final String avatar;
  const BotConfig(this.position, this.name, this.avatar);
}

const botPlayers = {
  'RIGHT': BotConfig(PlayerPosition.right, 'سالم', 'https://picsum.photos/id/65/100/100'),
  'TOP': BotConfig(PlayerPosition.top, 'شريكي', 'https://picsum.photos/id/66/100/100'),
  'LEFT': BotConfig(PlayerPosition.left, 'عمر', 'https://picsum.photos/id/67/100/100'),
};

/// Visual assets
class VisualAsset {
  final String id;
  final String name;
  final String type;
  final String value;
  const VisualAsset(this.id, this.name, this.type, this.value);
}

const cardSkins = [
  VisualAsset('card_default', 'Royal Back', 'image', '/assets/royal_card_back.png'),
  VisualAsset('card_classic_blue', 'Classic Blue', 'css', 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)'),
  VisualAsset('card_classic_red', 'Classic Red', 'css', 'linear-gradient(135deg, #991b1b 0%, #ef4444 100%)'),
  VisualAsset('card_modern_black', 'Modern Black', 'css', 'linear-gradient(135deg, #000000 0%, #444444 100%)'),
];

const tableSkins = [
  VisualAsset('table_default', 'Premium Wood', 'image', 'PREMIUM_ASSETS'),
  VisualAsset('table_classic_green', 'Classic Green', 'css', '#1a472a'),
  VisualAsset('table_royal_blue', 'Royal Blue', 'css', '#1e3a8a'),
  VisualAsset('table_midnight', 'Midnight', 'css', '#0f172a'),
];

/// API configuration
class ApiConfig {
  static const String defaultUrl = 'http://localhost:3005';

  static String get baseUrl {
    return const String.fromEnvironment('API_URL', defaultValue: defaultUrl);
  }
}
