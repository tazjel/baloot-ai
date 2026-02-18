/// profile_screen.dart — Player profile with stats and match history.
///
/// Shows:
/// - Player avatar and name
/// - Win/loss stats with visual breakdown
/// - Recent match history from persistence
/// - League tier display
library;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/colors.dart';
import '../models/enums.dart';
import '../services/settings_persistence.dart';

/// Player profile screen with stats and match history.
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  String _playerName = '';
  int _gamesPlayed = 0;
  int _gamesWon = 0;
  List<MatchSummary> _matchHistory = [];
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final name = await SettingsPersistence.loadPlayerName();
    final stats = await SettingsPersistence.loadStats();
    final history = await SettingsPersistence.loadMatchHistory();
    if (mounted) {
      setState(() {
        _playerName = name ?? 'لاعب';
        _gamesPlayed = stats.played;
        _gamesWon = stats.won;
        _matchHistory = history;
        _loaded = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final winRate = _gamesPlayed > 0 ? (_gamesWon / _gamesPlayed * 100) : 0.0;
    final tier = LeagueTier.fromPoints(_gamesWon * 100); // simplified tier calc

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
          child: _loaded
              ? SingleChildScrollView(
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
                            'الملف الشخصي',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const Spacer(),
                          const SizedBox(width: 48), // Balance the back button
                        ],
                      ),

                      const SizedBox(height: 24),

                      // Avatar
                      Container(
                        width: 100,
                        height: 100,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: LinearGradient(
                            colors: [
                              AppColors.goldPrimary,
                              AppColors.goldDark,
                            ],
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
                          Icons.person_rounded,
                          size: 50,
                          color: Colors.white,
                        ),
                      ),

                      const SizedBox(height: 16),

                      // Player name with edit button
                      GestureDetector(
                        onTap: _editName,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              _playerName,
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Icon(
                              Icons.edit_rounded,
                              size: 18,
                              color: AppColors.goldPrimary.withOpacity(0.7),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 8),

                      // League tier badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: _tierColor(tier).withOpacity(0.15),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: _tierColor(tier).withOpacity(0.5),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              _tierIcon(tier),
                              color: _tierColor(tier),
                              size: 16,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              _tierLabel(tier),
                              style: TextStyle(
                                color: _tierColor(tier),
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 32),

                      // Stats cards
                      Row(
                        children: [
                          Expanded(
                            child: _StatCard(
                              icon: Icons.sports_esports_rounded,
                              value: '$_gamesPlayed',
                              label: 'مباريات',
                              color: AppColors.info,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _StatCard(
                              icon: Icons.emoji_events_rounded,
                              value: '$_gamesWon',
                              label: 'انتصارات',
                              color: AppColors.goldPrimary,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _StatCard(
                              icon: Icons.percent_rounded,
                              value: '${winRate.round()}%',
                              label: 'نسبة الفوز',
                              color: AppColors.success,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 24),

                      // Win rate progress ring
                      if (_gamesPlayed > 0)
                        _WinRateRing(
                          winRate: winRate / 100,
                          gamesPlayed: _gamesPlayed,
                          gamesWon: _gamesWon,
                        ),

                      // Match history
                      if (_matchHistory.isNotEmpty) ...[
                        const SizedBox(height: 24),
                        const Align(
                          alignment: Alignment.centerRight,
                          child: Text(
                            'آخر المباريات',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: AppColors.textGold,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        ..._matchHistory.take(10).map((match) {
                          final timeAgo = _formatTimeAgo(match.date);
                          return Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 12,
                            ),
                            decoration: BoxDecoration(
                              color: match.won
                                  ? AppColors.success.withOpacity(0.08)
                                  : AppColors.error.withOpacity(0.08),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: match.won
                                    ? AppColors.success.withOpacity(0.2)
                                    : AppColors.error.withOpacity(0.2),
                              ),
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  match.won
                                      ? Icons.emoji_events_rounded
                                      : Icons.close_rounded,
                                  color: match.won
                                      ? AppColors.goldPrimary
                                      : AppColors.error,
                                  size: 20,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        match.won ? 'فوز' : 'خسارة',
                                        style: TextStyle(
                                          fontWeight: FontWeight.bold,
                                          color: match.won
                                              ? AppColors.success
                                              : AppColors.error,
                                        ),
                                      ),
                                      Text(
                                        '${match.rounds} جولات • ${match.difficulty}',
                                        style: const TextStyle(
                                          color: AppColors.textMuted,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Text(
                                  '${match.usScore} - ${match.themScore}',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  timeAgo,
                                  style: const TextStyle(
                                    color: AppColors.textMuted,
                                    fontSize: 10,
                                  ),
                                ),
                              ],
                            ),
                          );
                        }),
                      ],

                      const SizedBox(height: 24),

                      // Empty state or hint
                      if (_gamesPlayed == 0)
                        Container(
                          padding: const EdgeInsets.all(24),
                          decoration: BoxDecoration(
                            color: AppColors.primaryWithOpacity,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: AppColors.goldPrimary.withOpacity(0.3),
                            ),
                          ),
                          child: const Column(
                            children: [
                              Icon(
                                Icons.sports_esports_outlined,
                                size: 48,
                                color: AppColors.goldPrimary,
                              ),
                              SizedBox(height: 12),
                              Text(
                                'لم تلعب أي مباراة بعد',
                                style: TextStyle(
                                  color: AppColors.textMuted,
                                  fontSize: 16,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text(
                                'ابدأ مباراة جديدة لتبدأ رحلتك!',
                                style: TextStyle(
                                  color: AppColors.textMuted,
                                  fontSize: 13,
                                ),
                              ),
                            ],
                          ),
                        ),

                      // Reset stats button (only shown if stats exist)
                      if (_gamesPlayed > 0) ...[
                        const SizedBox(height: 32),
                        TextButton.icon(
                          onPressed: _confirmResetStats,
                          icon: const Icon(Icons.delete_outline_rounded, size: 18),
                          label: const Text('مسح الإحصائيات'),
                          style: TextButton.styleFrom(
                            foregroundColor: AppColors.error.withOpacity(0.7),
                          ),
                        ),
                      ],
                    ],
                  ),
                )
              : const Center(
                  child: CircularProgressIndicator(
                    color: AppColors.goldPrimary,
                  ),
                ),
        ),
      ),
    );
  }

  void _confirmResetStats() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('مسح الإحصائيات'),
        content: const Text('هل أنت متأكد من مسح جميع الإحصائيات وسجل المباريات؟ لا يمكن التراجع.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(ctx);
              await SettingsPersistence.resetStats();
              if (mounted) {
                setState(() {
                  _gamesPlayed = 0;
                  _gamesWon = 0;
                  _matchHistory = [];
                });
              }
            },
            child: const Text('مسح', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
  }

  void _editName() {
    final controller = TextEditingController(text: _playerName);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تغيير الاسم'),
        content: TextField(
          controller: controller,
          autofocus: true,
          textAlign: TextAlign.right,
          decoration: const InputDecoration(
            hintText: 'أدخل اسمك',
            border: OutlineInputBorder(),
          ),
          maxLength: 20,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () {
              final newName = controller.text.trim();
              if (newName.isNotEmpty) {
                setState(() => _playerName = newName);
                SettingsPersistence.savePlayerName(newName);
              }
              Navigator.pop(ctx);
            },
            child: const Text(
              'حفظ',
              style: TextStyle(color: AppColors.goldPrimary),
            ),
          ),
        ],
      ),
    );
  }

  Color _tierColor(LeagueTier tier) {
    switch (tier) {
      case LeagueTier.bronze:
        return const Color(0xFFCD7F32);
      case LeagueTier.silver:
        return const Color(0xFFC0C0C0);
      case LeagueTier.gold:
        return AppColors.goldPrimary;
      case LeagueTier.platinum:
        return const Color(0xFF00CED1);
      case LeagueTier.diamond:
        return const Color(0xFF00BFFF);
      case LeagueTier.grandmaster:
        return const Color(0xFFFF4500);
    }
  }

  IconData _tierIcon(LeagueTier tier) {
    switch (tier) {
      case LeagueTier.bronze:
        return Icons.shield_outlined;
      case LeagueTier.silver:
        return Icons.shield_rounded;
      case LeagueTier.gold:
        return Icons.emoji_events_rounded;
      case LeagueTier.platinum:
        return Icons.diamond_outlined;
      case LeagueTier.diamond:
        return Icons.diamond_rounded;
      case LeagueTier.grandmaster:
        return Icons.military_tech_rounded;
    }
  }

  String _tierLabel(LeagueTier tier) {
    switch (tier) {
      case LeagueTier.bronze:
        return 'برونز';
      case LeagueTier.silver:
        return 'فضي';
      case LeagueTier.gold:
        return 'ذهبي';
      case LeagueTier.platinum:
        return 'بلاتيني';
      case LeagueTier.diamond:
        return 'ماسي';
      case LeagueTier.grandmaster:
        return 'جراند ماستر';
    }
  }

  String _formatTimeAgo(DateTime date) {
    final diff = DateTime.now().difference(date);
    if (diff.inMinutes < 60) return 'منذ ${diff.inMinutes} د';
    if (diff.inHours < 24) return 'منذ ${diff.inHours} س';
    if (diff.inDays < 7) return 'منذ ${diff.inDays} ي';
    return '${date.day}/${date.month}';
  }
}

// =============================================================================
// Stat Card
// =============================================================================

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  final Color color;

  const _StatCard({
    required this.icon,
    required this.value,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: const TextStyle(
              color: AppColors.textMuted,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// Win Rate Ring
// =============================================================================

class _WinRateRing extends StatelessWidget {
  final double winRate;
  final int gamesPlayed;
  final int gamesWon;

  const _WinRateRing({
    required this.winRate,
    required this.gamesPlayed,
    required this.gamesWon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.cardSurface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.darkBorder),
      ),
      child: Row(
        children: [
          // Ring
          SizedBox(
            width: 80,
            height: 80,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 80,
                  height: 80,
                  child: CircularProgressIndicator(
                    value: winRate,
                    strokeWidth: 6,
                    backgroundColor: AppColors.error.withOpacity(0.2),
                    valueColor: const AlwaysStoppedAnimation(AppColors.success),
                  ),
                ),
                Text(
                  '${(winRate * 100).round()}%',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textLight,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 20),
          // Legend
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'نسبة الفوز',
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Container(
                      width: 12,
                      height: 12,
                      decoration: const BoxDecoration(
                        color: AppColors.success,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'فوز: $gamesWon',
                      style: const TextStyle(
                        color: AppColors.textLight,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Container(
                      width: 12,
                      height: 12,
                      decoration: BoxDecoration(
                        color: AppColors.error.withOpacity(0.5),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'خسارة: ${gamesPlayed - gamesWon}',
                      style: const TextStyle(
                        color: AppColors.textLight,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
