/// leaderboard_screen.dart — Top players ranking screen.
///
/// Shows the player's own rank at the top, then a scrollable list of
/// the top 50 players with tier badges and medal icons for top 3.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/colors.dart';
import '../services/leaderboard_service.dart';
import '../widgets/tier_badge.dart';

/// Provider for the leaderboard service.
final leaderboardServiceProvider = Provider<LeaderboardService>((ref) {
  return LeaderboardService();
});

/// Leaderboard screen with pull-to-refresh.
class LeaderboardScreen extends ConsumerStatefulWidget {
  const LeaderboardScreen({super.key});

  @override
  ConsumerState<LeaderboardScreen> createState() => _LeaderboardScreenState();
}

class _LeaderboardScreenState extends ConsumerState<LeaderboardScreen> {
  List<LeaderboardEntry>? _entries;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final service = ref.read(leaderboardServiceProvider);
      final entries = await service.fetchLeaderboard();
      if (mounted) {
        setState(() {
          _entries = entries;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppColors.darkBg,
        appBar: AppBar(
          title: const Text(
            'لوحة المتصدرين',
            style: TextStyle(
              color: AppColors.goldPrimary,
              fontWeight: FontWeight.bold,
            ),
          ),
          backgroundColor: AppColors.darkSurface,
          iconTheme: const IconThemeData(color: AppColors.goldPrimary),
          elevation: 0,
        ),
        body: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.goldPrimary),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, color: AppColors.error, size: 48),
            const SizedBox(height: 16),
            Text(
              'حدث خطأ في تحميل البيانات',
              style: const TextStyle(color: AppColors.textMuted, fontSize: 16),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _fetchData,
              icon: const Icon(Icons.refresh),
              label: const Text('إعادة المحاولة'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.goldPrimary,
                foregroundColor: Colors.black,
              ),
            ),
          ],
        ),
      );
    }

    final entries = _entries ?? [];

    return RefreshIndicator(
      onRefresh: _fetchData,
      color: AppColors.goldPrimary,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: entries.length,
        itemBuilder: (context, index) {
          final entry = entries[index];
          return _LeaderboardTile(entry: entry);
        },
      ),
    );
  }
}

/// A single leaderboard row with rank, name, points, and tier.
class _LeaderboardTile extends StatelessWidget {
  final LeaderboardEntry entry;

  const _LeaderboardTile({required this.entry});

  /// Medal icon for top 3 ranks.
  Widget? get _medalIcon {
    switch (entry.rank) {
      case 1:
        return const Text('🥇', style: TextStyle(fontSize: 24));
      case 2:
        return const Text('🥈', style: TextStyle(fontSize: 24));
      case 3:
        return const Text('🥉', style: TextStyle(fontSize: 24));
      default:
        return null;
    }
  }

  /// Determine tier from league points.
  String get _tier {
    final pts = entry.leaguePoints;
    if (pts >= 1800) return 'Grandmaster';
    if (pts >= 1500) return 'Master';
    if (pts >= 1200) return 'Expert';
    if (pts >= 900) return 'Intermediate';
    return 'Beginner';
  }

  @override
  Widget build(BuildContext context) {
    final isTopThree = entry.rank <= 3;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: isTopThree
            ? AppColors.goldPrimary.withAlpha(20)
            : AppColors.darkCard,
        borderRadius: BorderRadius.circular(12),
        border: isTopThree
            ? Border.all(color: AppColors.goldPrimary.withAlpha(60))
            : null,
      ),
      child: Row(
        children: [
          // Rank number or medal
          SizedBox(
            width: 40,
            child: _medalIcon ??
                Text(
                  '${entry.rank}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
          ),
          const SizedBox(width: 12),

          // Player name
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${entry.firstName} ${entry.lastName}',
                  style: TextStyle(
                    color: isTopThree
                        ? AppColors.goldPrimary
                        : AppColors.textLight,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                TierBadge(tier: _tier, fontSize: 10),
              ],
            ),
          ),

          // League points
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${entry.leaguePoints}',
                style: const TextStyle(
                  color: AppColors.goldPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Text(
                'نقطة',
                style: TextStyle(color: AppColors.textMuted, fontSize: 11),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
