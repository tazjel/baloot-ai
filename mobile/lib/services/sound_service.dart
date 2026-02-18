import 'package:audioplayers/audioplayers.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SoundService {
  static final SoundService _instance = SoundService._internal();

  factory SoundService() => _instance;

  SoundService._internal() {
    _loadFromPrefs();
  }

  static const String _prefPrefix = 'baloot_sound_';

  // Volume categories mirroring frontend/src/services/SoundManager.ts
  final Map<String, double> _volumes = {
    'cards': 1.0,
    'ui': 1.0,
    'events': 1.0,
    'bids': 1.0,
  };

  bool _isMuted = false;

  /// Load saved sound settings from SharedPreferences.
  Future<void> _loadFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _isMuted = prefs.getBool('${_prefPrefix}muted') ?? false;
      for (final key in _volumes.keys) {
        final saved = prefs.getDouble('$_prefPrefix$key');
        if (saved != null) _volumes[key] = saved.clamp(0.0, 1.0);
      }
    } catch (_) {}
  }

  /// Persist current settings to SharedPreferences.
  Future<void> _saveToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('${_prefPrefix}muted', _isMuted);
      for (final entry in _volumes.entries) {
        await prefs.setDouble('$_prefPrefix${entry.key}', entry.value);
      }
    } catch (_) {}
  }

  void setMute(bool muted) {
    _isMuted = muted;
    _saveToPrefs();
  }

  bool get isMuted => _isMuted;

  void setVolume(String category, double volume) {
    if (_volumes.containsKey(category)) {
      _volumes[category] = volume.clamp(0.0, 1.0);
      _saveToPrefs();
    }
  }

  double getVolume(String category) => _volumes[category] ?? 1.0;

  Future<void> _play(String assetName, String category) async {
    if (_isMuted) return;
    final vol = _volumes[category] ?? 1.0;
    if (vol <= 0) return;

    try {
      // Create a new player for each sound to allow overlapping playback (fire-and-forget)
      final player = AudioPlayer();
      
      // Auto-dispose player after completion
      player.onPlayerComplete.listen((event) {
        player.dispose();
      });

      await player.play(AssetSource('sounds/$assetName.mp3'), volume: vol);
    } catch (_) {
      // Fail silently — audio errors should not affect gameplay.
    }
  }

  // ========================================
  // Card Sounds
  // ========================================
  Future<void> playCardSound() => _play('card_play', 'cards');
  Future<void> playShuffleSound() => _play('shuffle', 'cards');
  Future<void> playDealSequence() => _play('deal', 'cards');

  // ========================================
  // UI Sounds
  // ========================================
  Future<void> playTurnSound() => _play('turn', 'ui');
  Future<void> playErrorSound() => _play('error', 'ui');
  Future<void> playClick() => _play('click', 'ui');

  // ========================================
  // Event Sounds
  // ========================================
  Future<void> playWinSound() => _play('win_trick', 'events');
  Future<void> playProjectSound() => _play('project', 'events');
  Future<void> playAkkaSound() => _play('akka', 'events');
  Future<void> playKabootSound() => _play('kaboot', 'events');
  Future<void> playVictoryJingle() => _play('victory', 'events');
  Future<void> playDefeatJingle() => _play('defeat', 'events');

  // ========================================
  // Bid Sounds
  // ========================================
  Future<void> playPassSound() => _play('pass', 'bids');
  Future<void> playHokumSound() => _play('hokum', 'bids');
  Future<void> playSunSound() => _play('sun', 'bids');
  Future<void> playDoubleSound() => _play('double', 'bids');
}
