import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/colors.dart';
import '../models/enums.dart';

class VariantSelectionModal extends ConsumerWidget {
  final Function(String type, {String? suit}) onSelect;

  const VariantSelectionModal({
    super.key, 
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.surfaceDark,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.goldPrimary, width: 2),
        boxShadow: const [
          BoxShadow(
            color: Colors.black45,
            blurRadius: 16,
            spreadRadius: 4,
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'اختر نوع اللعب',
            style: TextStyle(
              color: AppColors.textLight,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 24),

          // Grid of options
          GridView.count(
            shrinkWrap: true,
            crossAxisCount: 3,
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.0,
            children: [
              _buildOption(
                label: 'شمس', 
                symbol: '☀', 
                color: Colors.amber, 
                onTap: () => onSelect('SUN'),
              ),
              _buildOption(
                label: 'حكم\n(هاس)', 
                symbol: '♥', 
                color: AppColors.suitHearts, 
                onTap: () => onSelect('HOKUM', suit: '♥'),
              ),
              _buildOption(
                label: 'حكم\n(ديمن)', 
                symbol: '♦', 
                color: AppColors.suitDiamonds, 
                onTap: () => onSelect('HOKUM', suit: '♦'),
              ),
              _buildOption(
                label: 'حكم\n(كلفس)', 
                symbol: '♣', 
                color: AppColors.suitClubs, 
                onTap: () => onSelect('HOKUM', suit: '♣'),
              ),
              _buildOption(
                label: 'حكم\n(سبيت)', 
                symbol: '♠', 
                color: AppColors.suitSpades, 
                onTap: () => onSelect('HOKUM', suit: '♠'),
              ),
              // Empty slot or Cancel?
              _buildOption(
                label: 'إلغاء', 
                symbol: '✕', 
                color: AppColors.textMuted, 
                onTap: () => Navigator.of(context).pop(), // Close modal
                isCancel: true,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildOption({
    required String label, 
    required String symbol, 
    required Color color, 
    required VoidCallback onTap,
    bool isCancel = false,
  }) {
    return Material(
      color: isCancel ? Colors.transparent : AppColors.surfaceLight,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          decoration: BoxDecoration(
            border: Border.all(color: isCancel ? Colors.transparent : color.withOpacity(0.5), width: 2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                symbol,
                style: TextStyle(
                  fontSize: 32,
                  color: color,
                  height: 1.0,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                label,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: isCancel ? AppColors.textMuted : Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
