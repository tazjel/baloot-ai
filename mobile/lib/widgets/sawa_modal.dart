import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/colors.dart';
import '../models/enums.dart';
import '../state/providers.dart';

class SawaModal extends ConsumerWidget {
  const SawaModal({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appState = ref.watch(gameStateProvider);
    final gameState = appState.gameState;
    final sawaState = gameState.sawaState;

    if (sawaState == null || !sawaState.active) {
      return const SizedBox.shrink();
    }

    if (gameState.players.isEmpty) return const SizedBox.shrink();
    final claimer = gameState.players.firstWhere(
      (p) => p.position == sawaState.claimer,
      orElse: () => gameState.players[0],
    );

    final isMeClaimer = sawaState.claimer == PlayerPosition.bottom;
    final myResponse = sawaState.responses[PlayerPosition.bottom.value];
    final hasResponded = myResponse != null;

    return Container(
      color: Colors.black54,
       child: Center(
        child: Container(
          width: 350,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: AppColors.surfaceDark,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.goldPrimary, width: 2),
            boxShadow: [
              BoxShadow(
                color: AppColors.goldPrimary.withAlpha(76),
                blurRadius: 20,
                spreadRadius: 5,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                '🤝 طلب سوا',
                style: TextStyle(
                  color: AppColors.goldPrimary,
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'اللاعب ${claimer.name} يطلب إنهاء الجولة بالتعادل (سوا).',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white, fontSize: 16),
              ),
              const SizedBox(height: 24),
              
              // Responses List
              ...PlayerPosition.values.map((pos) {
                if (pos == sawaState.claimer) return const SizedBox.shrink();
                
                final response = sawaState.responses[pos.value];
                final statusIcon = response == 'ACCEPTED' 
                    ? const Icon(Icons.check_circle, color: AppColors.success)
                    : response == 'REFUSED'
                        ? const Icon(Icons.cancel, color: AppColors.error)
                        : const SizedBox(
                            width: 20, 
                            height: 20, 
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.grey)
                          );

                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(pos.value, style: const TextStyle(color: AppColors.textLight)), // Ideally use player name
                      statusIcon,
                    ],
                  ),
                );
              }),

              const SizedBox(height: 24),

              // Actions
              if (!isMeClaimer && !hasResponded)
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: AppColors.error),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        onPressed: () => ref.read(gameSocketProvider.notifier).sendAction('SAWA_RESPONSE', payload: {'response': 'REFUSED'}),
                        child: const Text('رفض', style: TextStyle(color: AppColors.error)),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.success,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        onPressed: () => ref.read(gameSocketProvider.notifier).sendAction('SAWA_RESPONSE', payload: {'response': 'ACCEPTED'}),
                        child: const Text('موافقة', style: TextStyle(color: Colors.white)),
                      ),
                    ),
                  ],
                )
              else
                const Text(
                  'في انتظار بقية اللاعبين...',
                  style: TextStyle(color: AppColors.textMuted, fontStyle: FontStyle.italic),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
