/// tip_of_the_day.dart — Rotating gameplay tips for the lobby.
///
/// Shows a random Baloot strategy tip each time the lobby loads.
/// Tips cover bidding, playing, and general strategy.
library;
import 'dart:math';

import 'package:flutter/material.dart';

import '../core/theme/colors.dart';

/// A card widget that displays a random Baloot gameplay tip.
class TipOfTheDay extends StatefulWidget {
  const TipOfTheDay({super.key});

  @override
  State<TipOfTheDay> createState() => _TipOfTheDayState();
}

class _TipOfTheDayState extends State<TipOfTheDay> {
  late int _tipIndex;

  @override
  void initState() {
    super.initState();
    _tipIndex = Random().nextInt(_tips.length);
  }

  void _nextTip() {
    setState(() {
      _tipIndex = (_tipIndex + 1) % _tips.length;
    });
  }

  @override
  Widget build(BuildContext context) {
    final tip = _tips[_tipIndex];
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark
            ? AppColors.primaryWithOpacity
            : AppColors.goldPrimary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppColors.goldPrimary.withOpacity(0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                tip.icon,
                color: AppColors.goldPrimary,
                size: 18,
              ),
              const SizedBox(width: 8),
              Text(
                tip.category,
                style: const TextStyle(
                  color: AppColors.goldPrimary,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              GestureDetector(
                onTap: _nextTip,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'نصيحة أخرى',
                      style: TextStyle(
                        color: AppColors.goldPrimary.withOpacity(0.7),
                        fontSize: 11,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      Icons.refresh_rounded,
                      color: AppColors.goldPrimary.withOpacity(0.7),
                      size: 14,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            tip.text,
            style: TextStyle(
              color: isDark ? AppColors.textLight : AppColors.textDark,
              fontSize: 13,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _Tip {
  final IconData icon;
  final String category;
  final String text;

  const _Tip({
    required this.icon,
    required this.category,
    required this.text,
  });
}

const List<_Tip> _tips = [
  // Bidding tips
  _Tip(
    icon: Icons.gavel_rounded,
    category: 'المزايدة',
    text: 'إذا كان لديك 3 أوراق أو أكثر من نفس النوع مع الإكة أو الشايب، فكّر في المزايدة حكم.',
  ),
  _Tip(
    icon: Icons.gavel_rounded,
    category: 'المزايدة',
    text: 'صن تعطي نقاط أكثر لكن المخاطرة أعلى. تحتاج توزيع قوي في أكثر من نوع.',
  ),
  _Tip(
    icon: Icons.gavel_rounded,
    category: 'المزايدة',
    text: 'لا تتردد في قول "باس" إذا يدك ضعيفة. أحياناً الباس أذكى من المزايدة.',
  ),
  _Tip(
    icon: Icons.gavel_rounded,
    category: 'المزايدة',
    text: 'في الجولة الثانية من المزايدة، يمكنك اختيار أي نوع حكم — اختر النوع الأقوى عندك.',
  ),

  // Playing tips
  _Tip(
    icon: Icons.style_rounded,
    category: 'اللعب',
    text: 'في حكم، حاول تنظيف ورق الحكم من الخصم مبكراً بلعب الحكم القوي أولاً.',
  ),
  _Tip(
    icon: Icons.style_rounded,
    category: 'اللعب',
    text: 'إذا شريكك فاز بالأكلة، ارمي له ورقة بنقاط عالية (إكة أو عشرة).',
  ),
  _Tip(
    icon: Icons.style_rounded,
    category: 'اللعب',
    text: 'تذكر الأوراق التي تم لعبها. إذا خرجت الإكة، الشايب يصبح أقوى ورقة.',
  ),
  _Tip(
    icon: Icons.style_rounded,
    category: 'اللعب',
    text: 'في صن، العشرة تساوي 10 نقاط والإكة 11. حافظ على أوراقك العالية للأكلات المهمة.',
  ),
  _Tip(
    icon: Icons.style_rounded,
    category: 'اللعب',
    text: 'إذا ما عندك من نوع الأكلة، يمكنك قطعها بورقة حكم (في وضع حكم فقط).',
  ),

  // Strategy tips
  _Tip(
    icon: Icons.psychology_rounded,
    category: 'استراتيجية',
    text: 'راقب أوراق الخصم — إذا لم يلعب نوعاً معيناً، غالباً ما عنده منه.',
  ),
  _Tip(
    icon: Icons.psychology_rounded,
    category: 'استراتيجية',
    text: 'المشاريع تعطي نقاط إضافية مجانية. تذكر الإعلان عن سرا، 50، 100 أو 400.',
  ),
  _Tip(
    icon: Icons.psychology_rounded,
    category: 'استراتيجية',
    text: 'البلوت (ملك + بنت الحكم) يعطي نقطتين إضافيتين. لا تنسَ الإعلان عنه!',
  ),
  _Tip(
    icon: Icons.psychology_rounded,
    category: 'استراتيجية',
    text: 'إذا الفريق الخصم قريب من 152، العب بحذر وحاول تأخير فوزهم.',
  ),
  _Tip(
    icon: Icons.psychology_rounded,
    category: 'استراتيجية',
    text: 'في حكم، الولد (J) هو أقوى ورقة والتسعة ثاني أقوى. لا تضيعهم بدري!',
  ),
];
