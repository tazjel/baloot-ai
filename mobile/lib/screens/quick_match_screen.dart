/// quick_match_screen.dart — Matchmaking queue UI for ranked play.
///
/// Shows a searching animation while the player is in the matchmaking queue.
/// Displays queue status (position, estimated wait) and allows cancellation.
/// On match found, navigates to the game screen.
library;

import 'dart:async';
import 'dart:developer' as dev;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/colors.dart';
import '../services/socket_service.dart';
import '../state/providers.dart';

/// Matchmaking queue screen for ranked "Quick Match" play.
class QuickMatchScreen extends ConsumerStatefulWidget {
  const QuickMatchScreen({super.key});

  @override
  ConsumerState<QuickMatchScreen> createState() => _QuickMatchScreenState();
}

class _QuickMatchScreenState extends ConsumerState<QuickMatchScreen>
    with SingleTickerProviderStateMixin {
  bool _searching = false;
  bool _matchFound = false;
  int _queueSize = 0;
  double _avgWait = 0;
  int _elapsedSeconds = 0;
  Timer? _timer;
  late AnimationController _pulseController;
  Function()? _matchFoundCleanup;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pulseController.dispose();
    _matchFoundCleanup?.call();
    super.dispose();
  }

  void _startSearch() {
    final socket = SocketService.instance;
    socket.connect();

    setState(() {
      _searching = true;
      _matchFound = false;
      _elapsedSeconds = 0;
    });

    // Start elapsed time counter
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _elapsedSeconds++);
    });

    // Listen for match_found event
    final rawSocket = socket.socket;
    if (rawSocket != null) {
      void onMatchFound(dynamic data) {
        if (!mounted) return;
        _timer?.cancel();
        final map = Map<String, dynamic>.from(data as Map);
        final roomId = map['roomId'] as String;
        final myIndex = map['yourIndex'] as int;

        dev.log('Match found! room=$roomId index=$myIndex', name: 'MATCH');

        setState(() => _matchFound = true);

        // Apply game state via socket notifier
        final socketNotifier = ref.read(gameSocketProvider.notifier);
        socketNotifier.joinGame(
          roomId: roomId,
          playerName: 'Player',
          myIndex: myIndex,
          onSuccess: () {
            if (mounted) context.go('/game');
          },
        );
      }

      rawSocket.on('match_found', onMatchFound);
      _matchFoundCleanup = () => rawSocket.off('match_found', onMatchFound);
    }

    // Join the queue
    rawSocket?.emit('queue_join', [
      {'playerName': 'Player'},
      (dynamic res) {
        final response = Map<String, dynamic>.from(
            res is Map ? res : (res is List && res.isNotEmpty ? res[0] as Map : {}));
        if (mounted && response['success'] == true) {
          setState(() {
            _queueSize = response['queueSize'] as int? ?? 0;
            _avgWait = (response['avgWait'] as num?)?.toDouble() ?? 0;
          });
        }
      },
    ]);
  }

  void _cancelSearch() {
    _timer?.cancel();
    _matchFoundCleanup?.call();
    _matchFoundCleanup = null;

    final rawSocket = SocketService.instance.socket;
    rawSocket?.emit('queue_leave', [
      {},
      (dynamic res) {
        dev.log('Left queue', name: 'MATCH');
      },
    ]);

    setState(() {
      _searching = false;
      _matchFound = false;
    });
  }

  String _formatTime(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppColors.darkBg,
        appBar: AppBar(
          backgroundColor: AppColors.darkSurface,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back, color: AppColors.goldPrimary),
            onPressed: () {
              if (_searching) _cancelSearch();
              context.pop();
            },
          ),
          title: const Text(
            'مباراة سريعة',
            style: TextStyle(
              color: AppColors.goldPrimary,
              fontFamily: 'IBM_Plex_Sans_Arabic',
              fontWeight: FontWeight.bold,
            ),
          ),
          centerTitle: true,
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: _searching ? _buildSearchingView() : _buildStartView(),
          ),
        ),
      ),
    );
  }

  Widget _buildStartView() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(
          Icons.sports_esports,
          size: 80,
          color: AppColors.goldPrimary,
        ),
        const SizedBox(height: 24),
        const Text(
          'العب مباراة مصنفة',
          style: TextStyle(
            color: AppColors.textLight,
            fontSize: 22,
            fontFamily: 'IBM_Plex_Sans_Arabic',
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'سيتم مطابقتك مع لاعبين بنفس مستواك',
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: 14,
            fontFamily: 'IBM_Plex_Sans_Arabic',
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 48),
        SizedBox(
          width: 220,
          height: 56,
          child: ElevatedButton(
            onPressed: _startSearch,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.goldPrimary,
              foregroundColor: AppColors.textDark,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
            ),
            child: const Text(
              'ابحث عن مباراة',
              style: TextStyle(
                fontSize: 18,
                fontFamily: 'IBM_Plex_Sans_Arabic',
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSearchingView() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Pulsing search icon
        AnimatedBuilder(
          animation: _pulseController,
          builder: (context, child) {
            return Transform.scale(
              scale: 0.8 + (_pulseController.value * 0.4),
              child: Icon(
                _matchFound ? Icons.check_circle : Icons.search,
                size: 80,
                color: _matchFound ? AppColors.success : AppColors.goldPrimary,
              ),
            );
          },
        ),
        const SizedBox(height: 24),
        Text(
          _matchFound ? 'تم العثور على مباراة!' : 'جاري البحث...',
          style: const TextStyle(
            color: AppColors.textLight,
            fontSize: 22,
            fontFamily: 'IBM_Plex_Sans_Arabic',
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        // Timer
        Text(
          _formatTime(_elapsedSeconds),
          style: const TextStyle(
            color: AppColors.goldPrimary,
            fontSize: 36,
            fontFamily: 'IBM_Plex_Sans_Arabic',
            fontWeight: FontWeight.w300,
          ),
        ),
        const SizedBox(height: 24),
        // Queue info
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.darkCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.darkBorder),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.people, color: AppColors.textMuted, size: 18),
              const SizedBox(width: 8),
              Text(
                'في الطابور: $_queueSize',
                style: const TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 14,
                  fontFamily: 'IBM_Plex_Sans_Arabic',
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 48),
        // Cancel button
        if (!_matchFound)
          TextButton(
            onPressed: _cancelSearch,
            child: const Text(
              'إلغاء البحث',
              style: TextStyle(
                color: AppColors.error,
                fontSize: 16,
                fontFamily: 'IBM_Plex_Sans_Arabic',
              ),
            ),
          ),
      ],
    );
  }
}
