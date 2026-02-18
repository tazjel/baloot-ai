/// dispute_modal.dart — Full 6-step Qayd dispute wizard.
///
/// Port of frontend/src/components/DisputeModal.tsx
///
/// Orchestrates the dispute flow through 6 steps:
/// 1. MAIN_MENU — Choose accusation type (reveal cards, wrong sawa, wrong akka)
/// 2. VIOLATION_SELECT — Pick specific violation (revoke, no trump, etc.)
/// 3. SELECT_CARD_1 — Pick crime card from trick history
/// 4. SELECT_CARD_2 — Pick proof card from trick history
/// 5. ADJUDICATION — Server evaluates (auto-transitions to RESULT)
/// 6. RESULT — Display verdict with penalty
///
/// Timer: 60s for human reporter, 2s for bot.
/// Auto-confirm result after 5s. Auto-cancel if no verdict after 10s.
library;
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/card_model.dart';
import '../models/enums.dart';
import '../models/game_state.dart';
import '../state/providers.dart';
import 'dispute/qayd_card_selector.dart';
import 'dispute/qayd_footer.dart';
import 'dispute/qayd_main_menu.dart';
import 'dispute/qayd_types.dart';
import 'dispute/qayd_verdict_panel.dart';

class DisputeModal extends ConsumerStatefulWidget {
  const DisputeModal({super.key});

  @override
  ConsumerState<DisputeModal> createState() => _DisputeModalState();
}

class _DisputeModalState extends ConsumerState<DisputeModal> {
  // Local UI state (mirrors server but allows optimistic step transitions)
  QaydStep _step = QaydStep.mainMenu;
  ViolationType? _violation;
  CardSelection? _crimeCard;
  CardSelection? _proofCard;
  int _timeLeft = 60;

  Timer? _timerInterval;
  Timer? _autoConfirmTimer;
  Timer? _fallbackTimer;

  @override
  void dispose() {
    _timerInterval?.cancel();
    _autoConfirmTimer?.cancel();
    _fallbackTimer?.cancel();
    super.dispose();
  }

  // ─── Send action to server ─────────────────────────────────────────────
  void _sendAction(String action, [Map<String, dynamic>? payload]) {
    ref
        .read(gameSocketProvider.notifier)
        .sendAction(action, payload: payload);
  }

  // ─── Derived state helpers ─────────────────────────────────────────────
  GameState get _gameState => ref.read(gameStateProvider).gameState;

  QaydState? get _qaydState => _gameState.qaydState;

  bool get _isReporter =>
      _qaydState?.reporter == PlayerPosition.bottom;

  bool get _isBot => _qaydState?.reporterIsBot ?? false;

  bool get _isHokum => _gameState.gameMode == GameMode.hokum;

  bool get _isDoubled => _gameState.doublingLevel.value >= 2;

  String get _reporterName {
    final pos = _qaydState?.reporter;
    if (pos == null) return 'غير معروف';
    for (final p in _gameState.players) {
      if (p.position == pos) return p.name;
    }
    return 'غير معروف';
  }

  int get _timerDuration => _isBot ? 2 : (_isReporter ? 60 : 2);

  List<ViolationData> get _violations {
    final list = _isHokum ? violationTypesHokum : violationTypesSun;
    if (!_isDoubled) {
      return list
          .where((v) => v.key != ViolationType.trumpInDouble)
          .toList();
    }
    return list;
  }

  List<TrickRecord> get _tricks {
    final gs = _gameState;
    final list = <TrickRecord>[
      ...(gs.currentRoundTricks ?? []),
    ];

    // Add current table cards as in-progress trick
    if (gs.tableCards.isNotEmpty) {
      list.add(TrickRecord(
        cards: gs.tableCards.map((tc) => {
              'card': tc.card.toJson(),
              'playedBy': tc.playedBy.value,
            }).toList(),
        playedBy: gs.tableCards.map((tc) => tc.playedBy.value).toList(),
      ));
    }

    return list;
  }

  VerdictData? get _verdictData {
    final qs = _qaydState;
    if (qs == null || qs.verdict == null) return null;
    final isCorrect = qs.verdict == 'CORRECT';
    return VerdictData(
      isCorrect: isCorrect,
      message: qs.verdictMessage ??
          (isCorrect ? 'قيد صحيح' : 'قيد خاطئ'),
      reason: qs.reason ?? '',
      penalty: qs.penaltyPoints ?? 0,
      loserTeam: qs.loserTeam,
    );
  }

  // ─── Step management ───────────────────────────────────────────────────

  void _syncWithServer() {
    final serverStep = _qaydState?.step;
    if (serverStep == QaydStep.result ||
        serverStep == QaydStep.adjudication) {
      if (_step != QaydStep.result) {
        setState(() => _step = QaydStep.result);
        _startAutoConfirm();
      }
    }
  }

  void _startTimer() {
    _timerInterval?.cancel();
    setState(() => _timeLeft = _timerDuration);

    if (_step == QaydStep.result || !_isReporter) return;

    _timerInterval = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        _timeLeft--;
        if (_timeLeft <= 0) {
          _timerInterval?.cancel();
          _sendAction('QAYD_CANCEL');
        }
      });
    });
  }

  void _startAutoConfirm() {
    _autoConfirmTimer?.cancel();
    _fallbackTimer?.cancel();

    final vd = _verdictData;
    if (vd != null) {
      // Auto-confirm after 5s
      _autoConfirmTimer = Timer(const Duration(seconds: 5), () {
        if (mounted) _sendAction('QAYD_CONFIRM');
      });
    } else {
      // Fallback: no verdict after 10s → auto-cancel
      _fallbackTimer = Timer(const Duration(seconds: 10), () {
        if (mounted) _sendAction('QAYD_CANCEL');
      });
    }
  }

  // ─── Handlers ──────────────────────────────────────────────────────────

  void _handleMenuSelect(MainMenuOption opt) {
    setState(() {
      _step = QaydStep.violationSelect;
    });
    _sendAction('QAYD_MENU_SELECT', {'option': opt.value});
  }

  void _handleViolationSelect(ViolationType v) {
    setState(() {
      _violation = v;
      _step = QaydStep.selectCard1;
    });
    _sendAction('QAYD_VIOLATION_SELECT', {'violation_type': v.value});
  }

  void _handleCardClick(
    CardModel card,
    int trickIdx,
    int cardIdx,
    String playedBy,
  ) {
    final sel = CardSelection(
      card: card,
      trickIdx: trickIdx,
      cardIdx: cardIdx,
      playedBy: playedBy,
    );

    if (_step == QaydStep.selectCard1) {
      setState(() {
        _crimeCard = sel;
        _step = QaydStep.selectCard2;
      });
      _sendAction('QAYD_SELECT_CRIME', {
        'suit': card.suit.symbol,
        'rank': card.rank.symbol,
        'trick_idx': trickIdx,
        'card_idx': cardIdx,
        'played_by': playedBy,
      });
    } else if (_step == QaydStep.selectCard2) {
      setState(() {
        _proofCard = sel;
        _step = QaydStep.result;
      });
      _sendAction('QAYD_SELECT_PROOF', {
        'suit': card.suit.symbol,
        'rank': card.rank.symbol,
        'trick_idx': trickIdx,
        'card_idx': cardIdx,
        'played_by': playedBy,
      });
      _startAutoConfirm();
    }
  }

  void _handleBack() {
    setState(() {
      if (_step == QaydStep.selectCard2) {
        _proofCard = null;
        _step = QaydStep.selectCard1;
      } else if (_step == QaydStep.selectCard1) {
        _crimeCard = null;
        _step = QaydStep.violationSelect;
      } else if (_step == QaydStep.violationSelect) {
        _violation = null;
        _step = QaydStep.mainMenu;
        _sendAction('QAYD_CANCEL');
      }
    });
  }

  // ─── Build ─────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final appState = ref.watch(gameStateProvider);
    final qaydState = appState.gameState.qaydState;

    // Only show if Qayd is active
    if (qaydState == null ||
        !qaydState.active ||
        qaydState.step == QaydStep.idle) {
      return const SizedBox.shrink();
    }

    // Sync step with server state
    _syncWithServer();

    // Start timer on first build / step change
    if (_timerInterval == null || !_timerInterval!.isActive) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && _step != QaydStep.result) _startTimer();
      });
    }

    final stepLabel = _stepLabel();

    return Container(
      color: const Color(0xBF000000), // rgba(0,0,0,0.75)
      child: Center(
        child: Container(
          width: MediaQuery.of(context).size.width * 0.92,
          constraints: const BoxConstraints(maxWidth: 500, maxHeight: 600),
          decoration: BoxDecoration(
            color: qaydBgDark,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.5),
                blurRadius: 24,
                spreadRadius: 4,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header
              _buildHeader(stepLabel),

              // Content
              Flexible(
                child: _buildContent(),
              ),

              // Footer
              QaydFooter(
                step: _step,
                timeLeft: _timeLeft,
                timerDuration: _timerDuration,
                reporterName: _reporterName,
                onBack: _handleBack,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(String stepLabel) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: const BoxDecoration(
        color: qaydBgDark,
        border: Border(bottom: BorderSide(color: qaydBorder)),
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Cancel button (hidden on result)
          if (_step != QaydStep.result)
            GestureDetector(
              onTap: () => _sendAction('QAYD_CANCEL'),
              child: Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.close, color: Color(0xFF9CA3AF), size: 20),
              ),
            )
          else
            const SizedBox(width: 32),

          // Step label
          Text(
            stepLabel,
            style: TextStyle(
              color: _stepLabelColor(),
              fontSize: 12,
            ),
          ),

          // Title
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'قيد',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
              const SizedBox(width: 6),
              Icon(Icons.shield, size: 18, color: const Color(0xFFFBBF24)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    switch (_step) {
      case QaydStep.mainMenu:
        return QaydMainMenu(
          isReporter: _isReporter,
          reporterName: _reporterName,
          onMenuSelect: _handleMenuSelect,
        );
      case QaydStep.violationSelect:
        return _buildViolationSelect();
      case QaydStep.selectCard1:
      case QaydStep.selectCard2:
        return QaydCardSelector(
          step: _step,
          tricks: _tricks,
          crimeCard: _crimeCard,
          proofCard: _proofCard,
          violations: _violations,
          violation: _violation,
          players: _gameState.players,
          onCardClick: _handleCardClick,
          onViolationSelect: _handleViolationSelect,
        );
      case QaydStep.result:
      case QaydStep.adjudication:
        return QaydVerdictPanel(
          verdictData: _verdictData,
          crimeCard: _crimeCard,
          proofCard: _proofCard,
        );
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildViolationSelect() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'اختر نوع المخالفة',
            style: TextStyle(color: Color(0xFFD1D5DB), fontSize: 15),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: _violations.map((v) {
              return Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => _handleViolationSelect(v.key),
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 12,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(12),
                      border:
                          Border.all(color: Colors.white.withOpacity(0.1)),
                    ),
                    child: Text(
                      v.ar,
                      style: const TextStyle(
                        color: Color(0xFFD1D5DB),
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  String _stepLabel() {
    switch (_step) {
      case QaydStep.mainMenu:
        return 'نوع القيد';
      case QaydStep.violationSelect:
        return 'المخالفة';
      case QaydStep.selectCard1:
        return 'الورقة الأولى';
      case QaydStep.selectCard2:
        return 'الورقة الثانية';
      case QaydStep.result:
      case QaydStep.adjudication:
        return 'النتيجة';
      default:
        return '';
    }
  }

  Color _stepLabelColor() {
    switch (_step) {
      case QaydStep.mainMenu:
      case QaydStep.violationSelect:
        return const Color(0xFFFBBF24); // Amber
      case QaydStep.selectCard1:
        return qaydCrimeColor; // Pink
      case QaydStep.selectCard2:
        return qaydProofColor; // Green
      case QaydStep.result:
      case QaydStep.adjudication:
        return Colors.white;
      default:
        return Colors.white;
    }
  }
}
