import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../state/ui/replay_notifier.dart';

class ReplayControls extends ConsumerWidget {
  const ReplayControls({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(replayProvider);
    final notifier = ref.read(replayProvider.notifier);

    if (!state.isActive) return const SizedBox.shrink();

    return Container(
        padding: const EdgeInsets.all(16),
        color: Colors.black.withOpacity(0.8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Game Replay', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white),
                  onPressed: notifier.exitReplay,
                ),
              ],
            ),
            Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.skip_previous, color: Colors.white),
                  onPressed: notifier.previous,
                ),
                IconButton(
                  icon: Icon(
                    state.isPlaying ? Icons.pause_circle_filled : Icons.play_circle_filled,
                    color: Colors.white,
                    size: 48,
                  ),
                  onPressed: notifier.togglePlay,
                ),
                IconButton(
                  icon: const Icon(Icons.skip_next, color: Colors.white),
                  onPressed: notifier.next,
                ),
                Expanded(
                  child: Slider(
                    value: state.currentIndex.toDouble(),
                    min: 0,
                    max: (state.totalSteps - 1).toDouble().clamp(0, 1000),
                    onChanged: (val) => notifier.jumpTo(val.toInt()),
                    activeColor: Colors.amber,
                  ),
                ),
                Text(
                  '${state.currentIndex + 1}/${state.totalSteps}',
                  style: const TextStyle(color: Colors.white70),
                ),
              ],
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _SpeedButton(label: '0.5x', speed: 0.5, current: state.playbackSpeed, onTap: notifier.setSpeed),
                _SpeedButton(label: '1x', speed: 1.0, current: state.playbackSpeed, onTap: notifier.setSpeed),
                _SpeedButton(label: '2x', speed: 2.0, current: state.playbackSpeed, onTap: notifier.setSpeed),
                _SpeedButton(label: '4x', speed: 4.0, current: state.playbackSpeed, onTap: notifier.setSpeed),
              ],
            ),
          ],
        ),
    );
  }
}

class _SpeedButton extends StatelessWidget {
  final String label;
  final double speed;
  final double current;
  final Function(double) onTap;

  const _SpeedButton({
    required this.label,
    required this.speed,
    required this.current,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isSelected = speed == current;
    return TextButton(
      onPressed: () => onTap(speed),
      child: Text(
        label,
        style: TextStyle(
          color: isSelected ? Colors.amber : Colors.white70,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        ),
      ),
    );
  }
}
