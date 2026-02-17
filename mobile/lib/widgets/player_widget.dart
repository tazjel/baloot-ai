import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/player.dart';
import '../state/audio/bot_speech_notifier.dart';

class PlayerWidget extends ConsumerWidget {
  final Player player;
  final int index;

  const PlayerWidget({super.key, required this.player, required this.index});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final speechState = ref.watch(botSpeechProvider);
    final isSpeaking = speechState.isSpeaking && speechState.speakerIndex == index;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (isSpeaking)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            margin: const EdgeInsets.only(bottom: 8),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Text(
              speechState.currentText ?? '',
              style: const TextStyle(color: Colors.black87, fontSize: 14),
            ),
          ),
        CircleAvatar(
          radius: 24,
          backgroundColor: Colors.white24,
          child: Text(
            player.name.substring(0, 1).toUpperCase(),
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          player.name,
          style: const TextStyle(color: Colors.white, fontSize: 12),
        ),
      ],
    );
  }
}
