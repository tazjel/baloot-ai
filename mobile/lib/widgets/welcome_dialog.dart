/// welcome_dialog.dart — First-launch welcome/tutorial dialog.
///
/// Shows a brief introduction to the game features
/// on the first app launch, then marks launch as complete.
library;
import 'package:flutter/material.dart';

import '../core/theme/colors.dart';
import '../services/settings_persistence.dart';

/// Shows the welcome dialog if this is the first launch.
///
/// Call from initState of the lobby screen.
Future<void> showWelcomeIfFirstLaunch(BuildContext context) async {
  final isFirst = await SettingsPersistence.isFirstLaunch();
  if (!isFirst || !context.mounted) return;

  await SettingsPersistence.markFirstLaunchComplete();

  if (!context.mounted) return;

  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => const _WelcomeDialog(),
  );
}

class _WelcomeDialog extends StatefulWidget {
  const _WelcomeDialog();

  @override
  State<_WelcomeDialog> createState() => _WelcomeDialogState();
}

class _WelcomeDialogState extends State<_WelcomeDialog> {
  int _page = 0;

  static const _pages = [
    _WelcomePage(
      icon: Icons.style_rounded,
      title: 'مرحباً ببلوت AI!',
      body: 'لعبة البلوت السعودية مع ذكاء اصطناعي متقدم.\n'
          'العب ضد بوتات بمستويات مختلفة أو العب مع أصدقائك عبر الإنترنت.',
    ),
    _WelcomePage(
      icon: Icons.psychology_rounded,
      title: '4 مستويات ذكاء',
      body: 'سهل — للمبتدئين\n'
          'متوسط — تحدي معتدل\n'
          'صعب — ذكاء حاد\n'
          'خالد — أصعب مستوى',
    ),
    _WelcomePage(
      icon: Icons.touch_app_rounded,
      title: 'كيف تلعب',
      body: 'اضغط على الورقة لاختيارها، ثم اضغط مرة أخرى للعبها.\n'
          'أثناء المزايدة، اختر صن أو حكم أو باس.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final page = _pages[_page];
    final isLast = _page == _pages.length - 1;

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      backgroundColor: AppColors.darkCard,
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Icon
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.primaryWithOpacity,
              ),
              child: Icon(page.icon, color: AppColors.goldPrimary, size: 36),
            ),

            const SizedBox(height: 20),

            // Title
            Text(
              page.title,
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: AppColors.goldPrimary,
              ),
            ),

            const SizedBox(height: 12),

            // Body
            Text(
              page.body,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: AppColors.textMuted,
                fontSize: 14,
                height: 1.6,
              ),
            ),

            const SizedBox(height: 24),

            // Page dots
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                _pages.length,
                (i) => Container(
                  width: i == _page ? 24 : 8,
                  height: 8,
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  decoration: BoxDecoration(
                    color: i == _page
                        ? AppColors.goldPrimary
                        : AppColors.textMuted.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ),
            ),

            const SizedBox(height: 20),

            // Buttons
            Row(
              children: [
                if (_page > 0)
                  TextButton(
                    onPressed: () => setState(() => _page--),
                    child: const Text(
                      'السابق',
                      style: TextStyle(color: AppColors.textMuted),
                    ),
                  ),
                const Spacer(),
                ElevatedButton(
                  onPressed: () {
                    if (isLast) {
                      Navigator.pop(context);
                    } else {
                      setState(() => _page++);
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.goldPrimary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 24,
                      vertical: 10,
                    ),
                  ),
                  child: Text(
                    isLast ? 'ابدأ اللعب!' : 'التالي',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _WelcomePage {
  final IconData icon;
  final String title;
  final String body;

  const _WelcomePage({
    required this.icon,
    required this.title,
    required this.body,
  });
}
