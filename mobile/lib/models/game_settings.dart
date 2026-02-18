/// GameSettings — All game configuration.
library;
import 'enums.dart';

class SoundVolumes {
  final double cards;
  final double ui;
  final double events;
  final double bids;

  const SoundVolumes({
    this.cards = 1.0,
    this.ui = 1.0,
    this.events = 1.0,
    this.bids = 1.0,
  });

  factory SoundVolumes.fromJson(Map<String, dynamic> json) {
    return SoundVolumes(
      cards: (json['cards'] as num?)?.toDouble() ?? 1.0,
      ui: (json['ui'] as num?)?.toDouble() ?? 1.0,
      events: (json['events'] as num?)?.toDouble() ?? 1.0,
      bids: (json['bids'] as num?)?.toDouble() ?? 1.0,
    );
  }

  Map<String, dynamic> toJson() => {
        'cards': cards,
        'ui': ui,
        'events': events,
        'bids': bids,
      };
}

class GameSettings {
  final double turnDuration;
  final bool strictMode;
  final bool soundEnabled;
  final String gameSpeed; // 'NORMAL' | 'FAST'
  final BotDifficulty? botDifficulty;
  final bool? isDebug;
  final bool? fourColorMode;
  final bool? highContrastMode;
  final String? cardLanguage; // 'EN' | 'AR'
  final AppThemeMode theme;
  final bool animationsEnabled;
  final SoundVolumes soundVolumes;
  final bool showHints;

  const GameSettings({
    this.turnDuration = 15.0,
    this.strictMode = true,
    this.soundEnabled = true,
    this.gameSpeed = 'NORMAL',
    this.botDifficulty,
    this.isDebug,
    this.fourColorMode,
    this.highContrastMode,
    this.cardLanguage,
    this.theme = AppThemeMode.auto,
    this.animationsEnabled = true,
    this.soundVolumes = const SoundVolumes(),
    this.showHints = false,
  });

  GameSettings copyWith({
    double? turnDuration,
    bool? strictMode,
    bool? soundEnabled,
    String? gameSpeed,
    BotDifficulty? botDifficulty,
    bool? isDebug,
    bool? fourColorMode,
    bool? highContrastMode,
    String? cardLanguage,
    AppThemeMode? theme,
    bool? animationsEnabled,
    SoundVolumes? soundVolumes,
    bool? showHints,
  }) {
    return GameSettings(
      turnDuration: turnDuration ?? this.turnDuration,
      strictMode: strictMode ?? this.strictMode,
      soundEnabled: soundEnabled ?? this.soundEnabled,
      gameSpeed: gameSpeed ?? this.gameSpeed,
      botDifficulty: botDifficulty ?? this.botDifficulty,
      isDebug: isDebug ?? this.isDebug,
      fourColorMode: fourColorMode ?? this.fourColorMode,
      highContrastMode: highContrastMode ?? this.highContrastMode,
      cardLanguage: cardLanguage ?? this.cardLanguage,
      theme: theme ?? this.theme,
      animationsEnabled: animationsEnabled ?? this.animationsEnabled,
      soundVolumes: soundVolumes ?? this.soundVolumes,
      showHints: showHints ?? this.showHints,
    );
  }

  factory GameSettings.fromJson(Map<String, dynamic> json) {
    return GameSettings(
      turnDuration: (json['turnDuration'] as num?)?.toDouble() ?? 15.0,
      strictMode: json['strictMode'] as bool? ?? true,
      soundEnabled: json['soundEnabled'] as bool? ?? true,
      gameSpeed: json['gameSpeed'] as String? ?? 'NORMAL',
      botDifficulty: json['botDifficulty'] != null
          ? BotDifficulty.fromValue(json['botDifficulty'] as String)
          : null,
      isDebug: json['isDebug'] as bool?,
      fourColorMode: json['fourColorMode'] as bool?,
      highContrastMode: json['highContrastMode'] as bool?,
      cardLanguage: json['cardLanguage'] as String?,
      theme: _parseTheme(json['theme']),
      animationsEnabled: json['animationsEnabled'] as bool? ?? true,
      soundVolumes: json['soundVolumes'] != null
          ? SoundVolumes.fromJson(json['soundVolumes'] as Map<String, dynamic>)
          : const SoundVolumes(),
      showHints: json['showHints'] as bool? ?? false,
    );
  }

  static AppThemeMode _parseTheme(dynamic value) {
    if (value == 'light') return AppThemeMode.light;
    if (value == 'dark') return AppThemeMode.dark;
    return AppThemeMode.auto;
  }

  Map<String, dynamic> toJson() => {
        'turnDuration': turnDuration,
        'strictMode': strictMode,
        'soundEnabled': soundEnabled,
        'gameSpeed': gameSpeed,
        if (botDifficulty != null) 'botDifficulty': botDifficulty!.value,
        if (isDebug != null) 'isDebug': isDebug,
        if (fourColorMode != null) 'fourColorMode': fourColorMode,
        if (highContrastMode != null) 'highContrastMode': highContrastMode,
        if (cardLanguage != null) 'cardLanguage': cardLanguage,
        'theme': theme == AppThemeMode.light
            ? 'light'
            : theme == AppThemeMode.dark
                ? 'dark'
                : 'auto',
        'animationsEnabled': animationsEnabled,
        'soundVolumes': soundVolumes.toJson(),
        'showHints': showHints,
      };
}
