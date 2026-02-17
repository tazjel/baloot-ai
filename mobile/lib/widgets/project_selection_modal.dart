import 'package:flutter/material.dart';
import '../core/theme/colors.dart';
import '../models/declared_project.dart';
import '../models/enums.dart';
import 'card_widget.dart';

class ProjectSelectionModal extends StatelessWidget {
  final List<DeclaredProject> projects;
  final VoidCallback onDeclare;
  final VoidCallback onSkip;

  const ProjectSelectionModal({
    super.key,
    required this.projects,
    required this.onDeclare,
    required this.onSkip,
  });

  @override
  Widget build(BuildContext context) {
    if (projects.isEmpty) return const SizedBox.shrink();

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
            'مشاريعك (Projects)',
            style: TextStyle(
              color: AppColors.goldPrimary,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          
          Container(
            constraints: const BoxConstraints(maxHeight: 300),
            child: SingleChildScrollView(
              child: Column(
                children: projects.map((p) => _buildProjectItem(p)).toList(),
              ),
            ),
          ),
          
          const SizedBox(height: 24),
          
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.grey),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onPressed: onSkip,
                  child: const Text('تخطي (Hide)', style: TextStyle(color: Colors.grey)),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.goldPrimary,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onPressed: onDeclare,
                  child: const Text('أعلن (Declare)', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildProjectItem(DeclaredProject project) {
    String label = '';
    switch (project.type) {
      case ProjectType.sira: label = 'سرا (Sira)'; break;
      case ProjectType.fifty: label = 'خمسين (Fifty)'; break;
      case ProjectType.hundred: label = 'مية (Hundred)'; break;
      case ProjectType.fourHundred: label = 'أربعمية (400)'; break;
      case ProjectType.baloot: label = 'بلوت (Baloot)'; break;
    }

    return Container(
  margin: const EdgeInsets.only(bottom: 12),
  padding: const EdgeInsets.all(12),
  decoration: BoxDecoration(
    color: Colors.black26,
    borderRadius: BorderRadius.circular(8),
    border: Border.all(color: Colors.white10),
  ),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          if (project.score != null)
            Text('${project.score} نقطة', style: const TextStyle(color: AppColors.goldPrimary)),
        ],
      ),
      const SizedBox(height: 8),
      if (project.cards != null && project.cards!.isNotEmpty)
        Wrap(
          spacing: -15, // Overlap cards slightly
          children: project.cards!.map((c) => CardWidget(
            card: c, 
            width: 40,
            isPlayable: false,
          )).toList(),
        ),
    ],
  ),
);
  }
}
