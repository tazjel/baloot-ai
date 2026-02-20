import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/colors.dart';
import '../services/leaderboard_service.dart';
import '../state/providers.dart';
import '../widgets/tier_badge.dart';

class LeaderboardScreen extends ConsumerStatefulWidget {
  const LeaderboardScreen({super.key});

  @override
  ConsumerState<LeaderboardScreen> createState() => _LeaderboardScreenState();
}

class _LeaderboardScreenState extends ConsumerState<LeaderboardScreen> {
  List<LeaderboardEntry>? _leaderboard;
  PlayerRating? _playerRating;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final service = ref.read(leaderboardServiceProvider);

      // Fetch leaderboard
      final leaderboardFuture = service.fetchLeaderboard();

      // Fetch player rating if logged in
      final auth = ref.read(authProvider);
      final email = auth.email;
      Future<PlayerRating?> ratingFuture = Future.value(null);

      if (email != null && email.isNotEmpty) {
        ratingFuture = service.fetchPlayerRating(email).then((value) => value).catchError((_) => null);
      }

      final results = await Future.wait([leaderboardFuture, ratingFuture]);

      if (mounted) {
        setState(() {
          _leaderboard = results[0] as List<LeaderboardEntry>;
          _playerRating = results[1] as PlayerRating?;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'تعذر تحميل البيانات. حاول مرة أخرى.';
          _isLoading = false;
        });
      }
    }
  }

  String _calculateTier(int points) {
    if (points >= 1800) return 'Grandmaster';
    if (points >= 1500) return 'Master';
    if (points >= 1200) return 'Expert';
    if (points >= 900) return 'Intermediate';
    return 'Beginner';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.darkBg,
      appBar: AppBar(
        title: const Text(
          'لوحة المتصدرين',
          style: TextStyle(
            color: AppColors.goldPrimary,
            fontFamily: 'Tajawal',
            fontWeight: FontWeight.bold,
          ),
        ),
        centerTitle: true,
        backgroundColor: AppColors.darkBg,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.goldPrimary),
      ),
      body: _buildBody(),
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
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, color: AppColors.error, size: 48),
            const SizedBox(height: 16),
            Text(
              _error!,
              style: const TextStyle(color: AppColors.textMuted, fontFamily: 'Tajawal'),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadData,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.goldPrimary,
                foregroundColor: Colors.black,
              ),
              child: const Text('إعادة المحاولة', style: TextStyle(fontFamily: 'Tajawal')),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadData,
      color: AppColors.goldPrimary,
      backgroundColor: AppColors.darkCard,
      child: Column(
        children: [
          if (_playerRating != null) _buildPlayerRankCard(),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _leaderboard?.length ?? 0,
              itemBuilder: (context, index) {
                final entry = _leaderboard![index];
                return _buildLeaderboardItem(entry);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlayerRankCard() {
    final rating = _playerRating!;
    final authState = ref.watch(authProvider);

    // If we have the rank from the leaderboard list, use it. Otherwise, maybe show rating?
    // The PlayerRating model doesn't have 'rank'.
    // We can try to find the player in the leaderboard list to get the rank.
    int? myRank;
    if (_leaderboard != null) {
      final index = _leaderboard!.indexWhere(
        (e) => e.firstName == authState.firstName && e.lastName == authState.lastName
      );
      if (index != -1) {
        myRank = _leaderboard![index].rank;
      }
    }

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.darkCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.goldPrimary.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          if (myRank != null)
             Text(
              '#$myRank',
              style: const TextStyle(
                color: AppColors.goldPrimary,
                fontWeight: FontWeight.bold,
                fontSize: 18,
                fontFamily: 'Tajawal',
              ),
            ),

          const SizedBox(width: 16),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'أنت', // "You"
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 12,
                    fontFamily: 'Tajawal',
                  ),
                ),
                Text(
                  authState.displayName,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    fontFamily: 'Tajawal',
                  ),
                ),
              ],
            ),
          ),

          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${rating.rating} نقطة',
                style: const TextStyle(
                  color: AppColors.goldPrimary,
                  fontWeight: FontWeight.bold,
                  fontFamily: 'Tajawal',
                ),
              ),
              const SizedBox(height: 4),
              TierBadge(tier: rating.tier),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLeaderboardItem(LeaderboardEntry entry) {
    final bool isTop3 = entry.rank <= 3;
    final String tier = _calculateTier(entry.leaguePoints);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.darkCard.withOpacity(0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.darkBorder),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 32,
            child: _buildRankWidget(entry.rank),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              '${entry.firstName} ${entry.lastName}',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontFamily: 'Tajawal',
              ),
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${entry.leaguePoints}',
                style: const TextStyle(
                  color: AppColors.goldPrimary,
                  fontWeight: FontWeight.bold,
                  fontFamily: 'Tajawal',
                ),
              ),
              const SizedBox(height: 4),
              TierBadge(tier: tier, fontSize: 10),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildRankWidget(int rank) {
    if (rank == 1) {
      return const Icon(Icons.emoji_events, color: Color(0xFFFFD700), size: 24); // Gold
    }
    if (rank == 2) {
      return const Icon(Icons.emoji_events, color: Color(0xFFC0C0C0), size: 24); // Silver
    }
    if (rank == 3) {
      return const Icon(Icons.emoji_events, color: Color(0xFFCD7F32), size: 24); // Bronze
    }
    return Text(
      '#$rank',
      style: const TextStyle(
        color: AppColors.textMuted,
        fontWeight: FontWeight.bold,
        fontFamily: 'Tajawal',
      ),
    );
  }
}
