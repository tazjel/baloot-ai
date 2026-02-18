/// action_dock.dart — Bottom action bar with phase-specific controls.
///
/// Port of frontend/src/components/ActionBar.tsx
///
/// The action dock switches between 5 modes based on game phase:
/// 1. **Bidding**: SUN / HOKUM / PASS buttons (+ ASHKAL / KAWESH)
/// 2. **Playing**: Double + Sawa + Qayd + Akka (HOKUM leading) + Fast-forward
/// 3. **Doubling**: Accept / Refuse double
/// 4. **Waiting**: Empty or "Add Bot" button
///
/// All buttons are Arabic-labeled with appropriate colors and icons.
library;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/colors.dart';
import '../models/card_model.dart';
import '../models/enums.dart';
import '../state/providers.dart';
import '../utils/akka_utils.dart';

/// Phase-aware action dock at the bottom of the game board.
///
/// Automatically switches between bidding controls, play controls,
/// and doubling controls based on the current game phase.
class ActionDock extends ConsumerWidget {
  const ActionDock({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appState = ref.watch(gameStateProvider);
    final gameState = appState.gameState;
    final rules = ref.watch(gameRulesProvider);
    final phase = gameState.phase;
    final isMyTurn = rules.isMyTurn;

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: _buildContent(context, ref, phase, isMyTurn, gameState),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    GamePhase phase,
    bool isMyTurn,
    dynamic gameState,
  ) {
    switch (phase) {
      case GamePhase.bidding:
        return isMyTurn
            ? _BiddingDock(key: const ValueKey('bidding'), gameState: gameState)
            : _WaitingTurnDock(key: const ValueKey('waiting-turn'));
      case GamePhase.playing:
        return _PlayingDock(key: const ValueKey('playing'), gameState: gameState);
      case GamePhase.doubling:
        return isMyTurn
            ? _DoublingDock(key: const ValueKey('doubling'))
            : _WaitingTurnDock(key: const ValueKey('waiting-double'));
      case GamePhase.waiting:
        return _LobbyDock(key: const ValueKey('lobby'));
      default:
        return const SizedBox.shrink(key: ValueKey('empty'));
    }
  }
}

// =============================================================================
// Bidding Dock
// =============================================================================

class _BiddingDock extends ConsumerWidget {
  final dynamic gameState;
  const _BiddingDock({super.key, required this.gameState});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final biddingRound = gameState.biddingRound as int;
    final isRound2 = biddingRound >= 2;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.6),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Phase label
            Text(
              isRound2 ? 'الجولة الثانية' : 'المزايدة',
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 8),
            // Bid buttons row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                // SUN button
                _BidButton(
                  label: 'صن',
                  color: AppColors.info,
                  icon: Icons.wb_sunny_rounded,
                  onTap: () => _bid(ref, 'SUN'),
                ),
                // HOKUM button
                _BidButton(
                  label: isRound2 ? 'حكم ثاني' : 'حكم',
                  color: AppColors.error,
                  icon: Icons.gavel_rounded,
                  onTap: () => _bid(ref, isRound2 ? 'HOKUM2' : 'HOKUM'),
                ),
                // PASS button
                _BidButton(
                  label: 'بس',
                  color: Colors.grey.shade700,
                  icon: Icons.block_rounded,
                  onTap: () => _bid(ref, 'PASS'),
                ),
                // ASHKAL (only available in certain conditions)
                if (!isRound2)
                  _BidButton(
                    label: 'أشكال',
                    color: AppColors.goldPrimary,
                    icon: Icons.auto_awesome,
                    onTap: () => _bid(ref, 'ASHKAL'),
                  ),
                // KAWESH (worthless hand — no court cards)
                if (_canKawesh(ref))
                  _BidButton(
                    label: 'كوش',
                    color: Colors.purple,
                    icon: Icons.refresh_rounded,
                    onTap: () => _bid(ref, 'KAWESH'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  bool _canKawesh(WidgetRef ref) {
    final appState = ref.watch(gameStateProvider);
    final hand = appState.gameState.players.isNotEmpty
        ? appState.gameState.players[0].hand
        : <CardModel>[];
    return hand.isNotEmpty && canDeclareKawesh(hand.cast<CardModel>());
  }

  void _bid(WidgetRef ref, String action) {
    HapticFeedback.lightImpact();
    ref.read(actionDispatcherProvider.notifier).handlePlayerAction(action);
  }
}

// =============================================================================
// Playing Dock
// =============================================================================

class _PlayingDock extends ConsumerWidget {
  final dynamic gameState;
  const _PlayingDock({super.key, required this.gameState});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rules = ref.watch(gameRulesProvider);
    final canDouble = rules.canDouble;
    final doublingLevel = gameState.doublingLevel as DoublingLevel;
    final isFastForwarding = gameState.isFastForwarding == true;
    final showAkka = _shouldShowAkka(ref);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.4),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Qayd (dispute) button
            _SmallButton(
              icon: Icons.shield_outlined,
              tooltip: 'قيد',
              onTap: () => ref
                  .read(actionDispatcherProvider.notifier)
                  .handlePlayerAction('QAYD_TRIGGER'),
            ),
            const SizedBox(width: 8),
            // Sawa (tie claim) button
            _SmallButton(
              icon: Icons.handshake_outlined,
              tooltip: 'سوا',
              onTap: () => ref
                  .read(actionDispatcherProvider.notifier)
                  .handlePlayerAction('SAWA_CLAIM'),
            ),
            const SizedBox(width: 8),
            // Akka button (HOKUM only, leading only)
            if (showAkka)
              _SmallButton(
                icon: Icons.workspace_premium,
                tooltip: 'أكة',
                onTap: () => ref
                    .read(actionDispatcherProvider.notifier)
                    .handlePlayerAction('AKKA'),
              ),
            if (showAkka) const SizedBox(width: 8),
            // Fast-forward toggle
            _SmallButton(
              icon: isFastForwarding
                  ? Icons.pause_rounded
                  : Icons.fast_forward_rounded,
              tooltip: isFastForwarding ? 'إيقاف' : 'تسريع',
              onTap: () {
                if (isFastForwarding) {
                  ref.read(actionDispatcherProvider.notifier).disableFastForward();
                } else {
                  ref.read(actionDispatcherProvider.notifier).enableFastForward();
                }
              },
            ),
            const SizedBox(width: 12),
            // Double button
            if (canDouble) ...[
              _ActionButton(
                label: _doubleLabel(doublingLevel),
                color: AppColors.warning,
                icon: Icons.bolt_rounded,
                onTap: () => ref
                    .read(actionDispatcherProvider.notifier)
                    .handlePlayerAction('DOUBLE'),
              ),
              const SizedBox(width: 12),
            ],
            // Info: current mode indicator
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    gameState.gameMode == GameMode.sun
                        ? Icons.wb_sunny_rounded
                        : Icons.gavel_rounded,
                    color: gameState.gameMode == GameMode.sun
                        ? AppColors.info
                        : AppColors.error,
                    size: 16,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    gameState.gameMode == GameMode.sun ? 'صن' : 'حكم',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (gameState.trumpSuit != null) ...[
                    const SizedBox(width: 4),
                    Text(
                      gameState.trumpSuit!.symbol,
                      style: TextStyle(
                        fontSize: 16,
                        color: gameState.trumpSuit!.isRed
                            ? AppColors.suitHearts
                            : AppColors.suitSpades,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  bool _shouldShowAkka(WidgetRef ref) {
    final appState = ref.watch(gameStateProvider);
    final gs = appState.gameState;
    if (gs.gameMode != GameMode.hokum) return false;
    if (gs.currentTurnIndex != 0) return false;
    if (gs.tableCards.isNotEmpty) return false;
    if (gs.players.isEmpty) return false;
    final hand = gs.players[0].hand;
    final trumpSuit = gs.bid.suit ?? gs.floorCard?.suit;
    return scanHandForAkka(
      hand: hand,
      tableCards: gs.tableCards,
      mode: GameMode.hokum,
      trumpSuit: trumpSuit,
      currentRoundTricks: gs.currentRoundTricks ?? [],
    );
  }

  String _doubleLabel(DoublingLevel level) {
    switch (level) {
      case DoublingLevel.normal:
        return 'دبل';
      case DoublingLevel.double_:
        return 'تربل';
      case DoublingLevel.triple:
        return 'كبوت';
      case DoublingLevel.quadruple:
        return 'قهوة';
      default:
        return 'دبل';
    }
  }
}

// =============================================================================
// Doubling Dock
// =============================================================================

class _DoublingDock extends ConsumerWidget {
  const _DoublingDock({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.6),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'تم رفع التحدي!',
              style: TextStyle(
                color: Colors.white.withOpacity(0.9),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _ActionButton(
                  label: 'قبول',
                  color: AppColors.success,
                  icon: Icons.check_rounded,
                  onTap: () => ref
                      .read(actionDispatcherProvider.notifier)
                      .handlePlayerAction('ACCEPT_DOUBLE'),
                ),
                _ActionButton(
                  label: 'رفض',
                  color: AppColors.error,
                  icon: Icons.close_rounded,
                  onTap: () => ref
                      .read(actionDispatcherProvider.notifier)
                      .handlePlayerAction('REFUSE_DOUBLE'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// Waiting Turn Dock
// =============================================================================

class _WaitingTurnDock extends StatelessWidget {
  const _WaitingTurnDock({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.3),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
      ),
      child: SafeArea(
        top: false,
        child: Center(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppColors.goldPrimary.withOpacity(0.6),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'في انتظار دورك...',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// Lobby Dock (Waiting for game start)
// =============================================================================

class _LobbyDock extends StatelessWidget {
  const _LobbyDock({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.4),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: SafeArea(
        top: false,
        child: Center(
          child: Text(
            'في انتظار بداية اللعبة...',
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 14,
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// Shared Button Widgets
// =============================================================================

class _BidButton extends StatelessWidget {
  final String label;
  final Color color;
  final IconData icon;
  final VoidCallback onTap;

  const _BidButton({
    required this.label,
    required this.color,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: color.withOpacity(0.2),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: color.withOpacity(0.5), width: 1.5),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  color: color,
                  fontSize: 13,
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

class _SmallButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  const _SmallButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            HapticFeedback.selectionClick();
            onTap();
          },
          borderRadius: BorderRadius.circular(10),
          child: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.white.withOpacity(0.15)),
            ),
            child: Icon(icon, color: Colors.white70, size: 18),
          ),
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final Color color;
  final IconData icon;
  final VoidCallback onTap;

  const _ActionButton({
    required this.label,
    required this.color,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}
