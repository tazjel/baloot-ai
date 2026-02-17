import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/enums.dart'; // For QaydStep
import '../core/theme/colors.dart';
import '../state/providers.dart';

class DisputeModal extends ConsumerStatefulWidget {
  const DisputeModal({super.key});

  @override
  ConsumerState<DisputeModal> createState() => _DisputeModalState();
}

class _DisputeModalState extends ConsumerState<DisputeModal> {
  // Helper to send actions via socket
  void _sendQaydAction(String action, [Map<String, dynamic>? payload]) {
    ref.read(gameSocketProvider.notifier).sendAction(action, payload: payload);
  }

  @override
  Widget build(BuildContext context) {
    final appState = ref.watch(gameStateProvider);
    final qaydState = appState.gameState.qaydState;

    // Only show if Qayd is active and not idle
    if (qaydState == null || !qaydState.active || qaydState.step == QaydStep.idle) {
      return const SizedBox.shrink();
    }

    return Container(
      color: Colors.black54, // Modal overlay logic should ideally be handled by parent or showDialog
      // However, if this is embedded in the main stack, this overlay works.
      child: Center(
        child: Container(
          width: MediaQuery.of(context).size.width * 0.9,
          constraints: const BoxConstraints(maxWidth: 400, maxHeight: 600),
          decoration: BoxDecoration(
            color: AppColors.surfaceDark,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.error, width: 2),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withAlpha(128),
                blurRadius: 20,
                spreadRadius: 5,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildHeader(),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: _buildStepContent(qaydState),
                ),
              ),
              _buildFooter(qaydState),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: AppColors.error,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(14),
          topRight: Radius.circular(14),
        ),
      ),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.gavel, color: Colors.white),
          SizedBox(width: 8),
          Text(
            'نظام القيد (Dispute)',
            style: TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStepContent(dynamic qaydState) {
    // Dynamic typing for qaydState to avoid circular deps if model isn't fully imported, 
    // but we imported enums.dart so we can cast if needed. 
    // Assuming qaydState is QaydState from game_state.dart
    
    final step = qaydState.step;

    if (step == QaydStep.mainMenu) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'اختر نوع المخالفة:',
            style: TextStyle(color: Colors.white, fontSize: 16),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),
          _buildOptionButton('REVOKE', 'رجوع عن حركة (Revoke)'),
          const SizedBox(height: 10),
          _buildOptionButton('WRONG_DEAL', 'توزيع خاطئ'),
          const SizedBox(height: 10),
          _buildOptionButton('ILLEGAL_PLAY', 'لعب غير قانوني'),
          const SizedBox(height: 10),
          _buildOptionButton('OTHER', 'أخرى'),
        ],
      );
    } else if (step == QaydStep.violationSelect) {
      return const Center(child: Text('سجل تفاصيل المخالفة...', style: TextStyle(color: Colors.white)));
    } else if (step == QaydStep.selectCard1) {
      return Column(
        children: [
          const Text('اختر الورقة محل الخلاف (Crime Card):', style: TextStyle(color: Colors.white)),
          const SizedBox(height: 16),
          // Placeholder for card picker
          Container(
             height: 100,
             color: Colors.white10,
             child: const Center(child: Text('Card Picker Placeholder', style: TextStyle(color: Colors.white54))),
          ),
        ],
      );
    } else if (step == QaydStep.adjudication) {
      return const Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(color: AppColors.goldPrimary),
          SizedBox(height: 16),
          Text('جاري التحقق من القيد...', style: TextStyle(color: Colors.white)),
        ],
      );
    } else if (step == QaydStep.result) {
      final isGuilty = qaydState.verdict == 'GUILTY';
      return Column(
        children: [
          Icon(
            isGuilty ? Icons.error_outline : Icons.check_circle_outline,
            color: isGuilty ? AppColors.error : AppColors.success,
            size: 64,
          ),
          const SizedBox(height: 16),
          Text(
            isGuilty ? 'مخالفة مؤكدة!' : 'لا توجد مخالفة',
            style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            qaydState.verdictMessage ?? '',
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.textMuted),
          ),
          if (qaydState.penaltyPoints != null && qaydState.penaltyPoints > 0)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Text(
                'غرامة: ${qaydState.penaltyPoints} نقطة',
                style: const TextStyle(color: AppColors.goldPrimary, fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
        ],
      );
    }

    return Text('Unknown Step: $step', style: const TextStyle(color: Colors.red));
  }

  Widget _buildOptionButton(String type, String label) {
    return ElevatedButton(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.surfaceLight,
        padding: const EdgeInsets.all(16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: AppColors.primaryWithOpacity),
        ),
      ),
      onPressed: () => _sendQaydAction('QAYD_SELECT_TYPE', {'type': type}),
      child: Text(label, style: const TextStyle(color: Colors.white, fontSize: 16)),
    );
  }

  Widget _buildFooter(dynamic qaydState) {
    final step = qaydState.step;

    if (step == QaydStep.adjudication) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: Colors.white12)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          if (step != QaydStep.result)
            TextButton(
              onPressed: () => _sendQaydAction('QAYD_CANCEL'),
              child: const Text('إلغاء', style: TextStyle(color: AppColors.textMuted)),
            )
          else 
            const SizedBox.shrink(), // Spacer or nothing
          
          if (step == QaydStep.result)
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.goldPrimary),
              onPressed: () => _sendQaydAction('QAYD_CONFIRM_RESULT'),
              child: const Text('موافق', style: TextStyle(color: Colors.black)),
            ),
        ],
      ),
    );
  }
}
