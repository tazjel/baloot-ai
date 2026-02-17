import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';
import '../../services/socket_service.dart';

class BotSpeechState {
  final String? currentText;
  final int? speakerIndex;
  final bool isSpeaking;

  const BotSpeechState({
    this.currentText,
    this.speakerIndex,
    this.isSpeaking = false,
  });

  BotSpeechState copyWith({
    String? currentText,
    int? speakerIndex,
    bool? isSpeaking,
  }) {
    return BotSpeechState(
      currentText: currentText ?? this.currentText,
      speakerIndex: speakerIndex ?? this.speakerIndex,
      isSpeaking: isSpeaking ?? this.isSpeaking,
    );
  }
}

class BotSpeechNotifier extends StateNotifier<BotSpeechState> {
  Function()? _unsubscribe;
  final FlutterTts _tts;

  BotSpeechNotifier([FlutterTts? tts]) 
      : _tts = tts ?? FlutterTts(), 
        super(const BotSpeechState()) {
    _initTts();
    _subscribeToSocket();
  }

  Future<void> _initTts() async {
    await _tts.setLanguage("ar-SA");
    await _tts.setPitch(1.0);
    await _tts.setSpeechRate(0.5);

    _tts.setStartHandler(() {
      if (mounted) {
        state = state.copyWith(isSpeaking: true);
      }
    });

    _tts.setCompletionHandler(() {
      if (mounted) {
        state = const BotSpeechState(); // Reset
      }
    });

    _tts.setErrorHandler((msg) {
      if (mounted) {
        state = const BotSpeechState();
      }
    });
  }

  void _subscribeToSocket() {
    _unsubscribe = SocketService.instance.onBotSpeak((playerIndex, text, emotion) {
      speak(playerIndex, text);
    });
  }

  Future<void> speak(int playerIndex, String text) async {
    state = BotSpeechState(
      currentText: text,
      speakerIndex: playerIndex,
      isSpeaking: true,
    );
    await _tts.speak(text);
  }

  Future<void> stop() async {
    await _tts.stop();
    state = const BotSpeechState();
  }

  @override
  void dispose() {
    _unsubscribe?.call();
    _tts.stop();
    super.dispose();
  }
}

final botSpeechProvider = StateNotifierProvider<BotSpeechNotifier, BotSpeechState>((ref) {
  return BotSpeechNotifier();
});
