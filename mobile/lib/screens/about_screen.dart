/// about_screen.dart — About/credits screen.
///
/// Shows:
/// - App version and build info
/// - Credits and technologies used
/// - Links to support/feedback
library;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/colors.dart';

/// About and credits screen.
class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: isDark
                ? [AppColors.darkBg, AppColors.darkSurface]
                : [AppColors.lightBg, AppColors.lightSurface],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                // Back button row
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back),
                      onPressed: () => context.go('/lobby'),
                    ),
                    const Spacer(),
                    const Text(
                      'حول التطبيق',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const Spacer(),
                    const SizedBox(width: 48),
                  ],
                ),

                const SizedBox(height: 32),

                // App logo
                Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      colors: [AppColors.goldLight, AppColors.goldDark],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.goldPrimary.withOpacity(0.3),
                        blurRadius: 16,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.style_rounded,
                    size: 50,
                    color: Colors.white,
                  ),
                ),

                const SizedBox(height: 16),

                const Text(
                  'بلوت AI',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: AppColors.goldPrimary,
                  ),
                ),

                const SizedBox(height: 4),

                Text(
                  'Baloot AI',
                  style: TextStyle(
                    fontSize: 14,
                    color: AppColors.textMuted,
                    letterSpacing: 2,
                  ),
                ),

                const SizedBox(height: 4),

                Text(
                  'الإصدار 1.0.0',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.textMuted,
                  ),
                ),

                const SizedBox(height: 32),

                // Description card
                _InfoCard(
                  icon: Icons.info_outline_rounded,
                  title: 'عن اللعبة',
                  children: const [
                    Text(
                      'بلوت AI هي لعبة بلوت سعودية مع ذكاء اصطناعي '
                      'متقدم. تدعم اللعب الفردي ضد البوت واللعب '
                      'الجماعي عبر الإنترنت.',
                      textAlign: TextAlign.right,
                      style: TextStyle(
                        color: AppColors.textMuted,
                        height: 1.6,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 12),

                // Features card
                _InfoCard(
                  icon: Icons.star_outline_rounded,
                  title: 'المميزات',
                  children: const [
                    _FeatureRow(icon: Icons.psychology_rounded, text: '4 مستويات ذكاء اصطناعي'),
                    _FeatureRow(icon: Icons.people_rounded, text: 'لعب جماعي عبر الإنترنت'),
                    _FeatureRow(icon: Icons.gavel_rounded, text: 'نظام قيد كامل'),
                    _FeatureRow(icon: Icons.emoji_events_rounded, text: 'إحصائيات وسجل مباريات'),
                    _FeatureRow(icon: Icons.dark_mode_rounded, text: 'الوضع الليلي'),
                    _FeatureRow(icon: Icons.vibration_rounded, text: 'اهتزازات لمسية'),
                  ],
                ),

                const SizedBox(height: 12),

                // Technologies card
                _InfoCard(
                  icon: Icons.code_rounded,
                  title: 'التقنيات',
                  children: const [
                    _TechRow(label: 'التطبيق', value: 'Flutter & Dart'),
                    _TechRow(label: 'الخادم', value: 'Python & FastAPI'),
                    _TechRow(label: 'الذكاء الاصطناعي', value: 'Custom Engine'),
                    _TechRow(label: 'الاتصال', value: 'WebSocket'),
                  ],
                ),

                const SizedBox(height: 12),

                // Game rules card
                _InfoCard(
                  icon: Icons.menu_book_rounded,
                  title: 'قواعد اللعبة',
                  children: const [
                    Text(
                      'بلوت هي لعبة ورق سعودية شهيرة تُلعب بـ 32 ورقة '
                      'بين فريقين. تتكون من مراحل المزايدة واللعب '
                      'والتسجيل. الفريق الأول الذي يصل إلى 152 نقطة يفوز.',
                      textAlign: TextAlign.right,
                      style: TextStyle(
                        color: AppColors.textMuted,
                        height: 1.6,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 32),

                // Footer
                const Text(
                  'صُنع بـ ❤️ في السعودية',
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 13,
                  ),
                ),

                const SizedBox(height: 4),

                const Text(
                  '© 2026 Baloot AI',
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 11,
                  ),
                ),

                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// Info Card
// =============================================================================

class _InfoCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final List<Widget> children;

  const _InfoCard({
    required this.icon,
    required this.title,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: AppColors.goldPrimary, size: 20),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }
}

// =============================================================================
// Feature Row
// =============================================================================

class _FeatureRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _FeatureRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, color: AppColors.goldPrimary, size: 18),
          const SizedBox(width: 10),
          Text(
            text,
            style: const TextStyle(
              color: AppColors.textMuted,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// Tech Row
// =============================================================================

class _TechRow extends StatelessWidget {
  final String label;
  final String value;

  const _TechRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: const TextStyle(
                color: AppColors.textMuted,
                fontSize: 13,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: AppColors.goldPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
