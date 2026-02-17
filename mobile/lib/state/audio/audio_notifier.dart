import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/game_state.dart';
import '../../models/enums.dart';
import '../../services/sound_service.dart';

// We don't need complex state for AudioNotifier as it's a side-effect manager,
// but we can store settings or status if we want. For now, empty state.
class AudioState {
  const AudioState();
}

class AudioNotifier extends StateNotifier<AudioState> {
  final Ref ref;
  final SoundService _sound;

  // Previous state trackers to detect changes
  int _prevTurnIndex = -1;
  int _prevTableLength = 0;
  bool _prevSawaActive = false;
  bool _prevProjectRevealing = false;
  GamePhase? _prevPhase;
  // Track declaration keys to detect new ones
  int _prevDeclarationCount = 0;

  AudioNotifier(this.ref, [SoundService? soundService]) 
      : _sound = soundService ?? SoundService(), 
        super(const AudioState());

  /// Call this whenever gameState changes to check for sound triggers.
  /// Ideally, this is called by a listener in the provider definition.
  void onGameStateChanged(GameState gameState) {
    if (gameState.phase == GamePhase.waiting) return;

    // 1. Your Turn Detection
    // Play sound if: it's my turn (index 0), it wasn't my turn before, and we are in Playing/Bidding phase.
    final isMyTurn = gameState.currentTurnIndex == 0;
    final wasMyTurn = _prevTurnIndex == 0;
    
    // Only play if phase is active
    final isPhaseActive = gameState.phase == GamePhase.playing || gameState.phase == GamePhase.bidding;

    if (isMyTurn && !wasMyTurn && isPhaseActive) {
      if (_prevTurnIndex != -1) { // Don't play on initial load
        _sound.playTurnSound();
      }
    }
    _prevTurnIndex = gameState.currentTurnIndex;

    // 2. Trick Completion (4 cards -> 0 cards)
    // When table clears, it means a trick was won.
    // If we transition from 4 cards to empty (or less), it usually means trick collected.
    // Ideally update loop: 0 -> 1 -> 2 -> 3 -> 4 -> (clear) -> 0
    final tableLen = gameState.tableCards.length;
    if (_prevTableLength == 4 && tableLen == 0) {
      _sound.playWinSound();
    }
    _prevTableLength = tableLen;

    // 3. Project Declarations
    // Check if total number of declarations increased
    int currentDeclCount = 0;
    for (final list in gameState.declarations.values) {
      currentDeclCount += list.length;
    }
    
    if (currentDeclCount > _prevDeclarationCount) {
       _sound.playProjectSound();
    }
    _prevDeclarationCount = currentDeclCount;

    // 4. Sawa Claim
    // If sawaState.active becomes true
    final isSawaActive = gameState.sawaState?.active ?? false;
    if (isSawaActive && !_prevSawaActive) {
       // Using Kaboot sound as a placeholder or generic alert if available, 
       // but strictly maybe we don't need a specific sound for Sawa start, 
       // just rely on visual. Or use 'events' sound.
       // _sound.playKabootSound(); 
    }
    _prevSawaActive = isSawaActive;

    // 5. Project Reveal Phase
    // If isProjectRevealing becomes true
    final isRevealing = gameState.isProjectRevealing ?? false;
    if (isRevealing && !_prevProjectRevealing) {
       // Already handled by declaration count mostly, but specifically for reveal phase start:
       // _sound.playProjectSound();
    }
    _prevProjectRevealing = isRevealing;

    // 6. Phase Transitions
    if (_prevPhase != gameState.phase) {
      if (gameState.phase == GamePhase.playing) {
         _sound.playDealSequence();
      }
    }
    _prevPhase = gameState.phase;
  }
}

// Provider
final audioNotifierProvider = StateNotifierProvider<AudioNotifier, AudioState>((ref) {
  return AudioNotifier(ref);
});
