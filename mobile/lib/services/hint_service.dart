import '../models/models.dart';
import '../utils/game_logic.dart';

class HintService {
  static const Map<String, int> _pointsSun = {
    'A': 11, '10': 10, 'K': 4, 'Q': 3, 'J': 2, '9': 0, '8': 0, '7': 0,
  };

  static const Map<String, int> _nonTrumpHokum = {
    'A': 11, '10': 10, 'K': 4, 'Q': 3, 'J': 0, '9': 0, '8': 0, '7': 0,
  };

  static const Map<String, int> _trumpHokum = {
    'J': 20, '9': 14, 'A': 11, '10': 10, 'K': 4, 'Q': 3, '8': 0, '7': 0,
  };

  static const Map<String, String> _suitSymbols = {
    '♥': '♥', '♦': '♦', '♣': '♣', '♠': '♠',
  };

  static int _getCardPoints(CardModel card, GameMode mode, [Suit? trumpSuit]) {
    if (mode == GameMode.sun) return _pointsSun[card.rank.symbol] ?? 0;
    if (card.suit == trumpSuit) return _trumpHokum[card.rank.symbol] ?? 0;
    return _nonTrumpHokum[card.rank.symbol] ?? 0;
  }

  static int _getCardStrength(CardModel card, GameMode mode, [Suit? trumpSuit]) {
    if (mode == GameMode.sun) {
      final order = ['A', '10', 'K', 'Q', 'J', '9', '8', '7'];
      return 8 - order.indexOf(card.rank.symbol);
    }
    if (card.suit == trumpSuit) {
      final trumps = ['J', '9', 'A', '10', 'K', 'Q', '8', '7'];
      return 20 + (8 - trumps.indexOf(card.rank.symbol));
    }
    final order = ['A', '10', 'K', 'Q', 'J', '9', '8', '7'];
    return 8 - order.indexOf(card.rank.symbol);
  }

  static int _calculateHandPoints(List<CardModel> hand, GameMode type, [Suit? trumpSuit]) {
    return hand.fold(0, (total, card) => total + _getCardPoints(card, type, trumpSuit));
  }

  static PlayerPosition _getPartnerPos(PlayerPosition myPos) {
    switch (myPos) {
      case PlayerPosition.bottom: return PlayerPosition.top;
      case PlayerPosition.top: return PlayerPosition.bottom;
      case PlayerPosition.right: return PlayerPosition.left;
      case PlayerPosition.left: return PlayerPosition.right;
    }
  }

  static String _suitLabel(Suit suit) => _suitSymbols[suit.symbol] ?? suit.symbol;

  static HintResult? getHint(GameState gameState) {
    if (gameState.players.isEmpty) return null;
    final player = gameState.players[0]; // Assuming human player at index 0

    if (gameState.phase == GamePhase.bidding || gameState.biddingPhase == 'GABLAK_WINDOW') {
      return getBiddingHint(gameState, player.hand);
    }
    if (gameState.phase == GamePhase.playing) {
      return getPlayingHint(gameState, player.hand, player.position);
    }
    return null;
  }

  static HintResult getBiddingHint(GameState gameState, List<CardModel> hand) {
    // 1. Evaluate SUN
    final sunPoints = _calculateHandPoints(hand, GameMode.sun);
    if (sunPoints >= 26) {
      return HintResult(
        action: 'SUN',
        reasoning: 'يدك قوية بالصن ($sunPoints نقطة) — اشترِ صن',
      );
    }

    // 2. ASHKAL (weak SUN)
    if (sunPoints >= 20 && sunPoints < 26) {
      return HintResult(
        action: 'ASHKAL',
        reasoning: 'صن متوسط ($sunPoints نقطة) — جرّب أشكال',
      );
    }

    // 3. Evaluate HOKUM per suit
    final suits = Suit.values;
    final suitsToCheck = gameState.biddingRound == 1 && gameState.floorCard != null
        ? [gameState.floorCard!.suit]
        : gameState.biddingRound == 2
            ? suits.where((s) => gameState.floorCard == null || s != gameState.floorCard!.suit).toList()
            : <Suit>[];

    int bestPoints = 0;
    Suit? bestSuit;
    bool bestHasJack = false;

    for (final s in suitsToCheck) {
      final handToTest = (gameState.biddingRound == 1 && gameState.floorCard != null)
          ? [...hand, gameState.floorCard!]
          : hand;

      final pts = _calculateHandPoints(handToTest, GameMode.hokum, s);
      final hasJack = handToTest.any((c) => c.suit == s && c.rank == Rank.jack);
      final modified = pts + (hasJack ? 10 : 0);

      if (modified > bestPoints) {
        bestPoints = modified;
        bestSuit = s;
        bestHasJack = hasJack;
      }
    }

    if (bestPoints >= 45 && bestSuit != null) {
      final jackNote = bestHasJack ? ' + الولد' : '';
      return HintResult(
        action: 'HOKUM',
        suit: bestSuit,
        reasoning: 'حكم ${_suitLabel(bestSuit!)} — $bestPoints نقطة$jackNote',
      );
    }

    return const HintResult(
      action: 'PASS',
      reasoning: 'يدك ضعيفة — بس',
    );
  }

  static HintResult getPlayingHint(GameState gameState, List<CardModel> hand, PlayerPosition playerPos) {
    GameMode actualMode = gameState.bid.type == GameMode.sun ? GameMode.sun : GameMode.hokum;

    Suit? trumpSuit;
    if (actualMode == GameMode.hokum) {
      trumpSuit = gameState.bid.suit ?? gameState.floorCard?.suit ?? Suit.spades;
    }

    final moves = hand.asMap().entries.map((entry) {
      final idx = entry.key;
      final card = entry.value;
      return _MoveCandidate(
        card: card,
        idx: idx,
        strength: _getCardStrength(card, actualMode, trumpSuit),
        points: _getCardPoints(card, actualMode, trumpSuit),
        isTrump: actualMode == GameMode.hokum && card.suit == trumpSuit,
      );
    }).where((m) => isValidMove(
      card: m.card,
      hand: hand,
      tableCards: gameState.tableCards,
      mode: actualMode,
      trumpSuit: trumpSuit,
      isLocked: gameState.isLocked,
    )).toList();

    if (moves.isEmpty) {
      return const HintResult(action: 'PLAY', cardIndex: 0, reasoning: 'العب أي ورقة');
    }

    if (moves.length == 1) {
      return HintResult(
        action: 'PLAY',
        cardIndex: moves[0].idx,
        reasoning: 'ورقة واحدة متاحة — ${moves[0].card.rank.symbol}${_suitLabel(moves[0].card.suit)}',
      );
    }

    moves.sort((a, b) => a.strength.compareTo(b.strength));

    final myPartnerPos = _getPartnerPos(playerPos);
    final didIBuy = gameState.bid.bidder == playerPos;

    // Leading
    if (gameState.tableCards.isEmpty) {
      if (actualMode == GameMode.hokum && didIBuy && trumpSuit != null) {
        final trumpMoves = moves.where((m) => m.isTrump).toList();
        if (trumpMoves.isNotEmpty) {
          final best = trumpMoves.last;
          return HintResult(
            action: 'PLAY',
            cardIndex: best.idx,
            reasoning: 'إبدأ بالحكم — اسحب أوراق الخصم (${best.card.rank.symbol}${_suitLabel(best.card.suit)})',
          );
        }
      }

      if (actualMode == GameMode.sun) {
        final aces = moves.where((m) => m.card.rank == Rank.ace).toList();
        if (aces.isNotEmpty) {
          return HintResult(
            action: 'PLAY',
            cardIndex: aces[0].idx,
            reasoning: 'إبدأ بالأكة — ورقة مضمونة (${aces[0].card.rank.symbol}${_suitLabel(aces[0].card.suit)})',
          );
        }
        final strongest = moves.last;
        return HintResult(
          action: 'PLAY',
          cardIndex: strongest.idx,
          reasoning: 'إبدأ بأقوى ورقة (${strongest.card.rank.symbol}${_suitLabel(strongest.card.suit)})',
        );
      }

      final strongest = moves.last;
      return HintResult(
        action: 'PLAY',
        cardIndex: strongest.idx,
        reasoning: 'إبدأ بأقوى ورقة (${strongest.card.rank.symbol}${_suitLabel(strongest.card.suit)})',
      );
    }

    // Following
    final winIdx = getTrickWinner(gameState.tableCards, actualMode, trumpSuit);
    final winningTableCard = gameState.tableCards[winIdx];
    final winnerPos = winningTableCard.playedBy;
    final isPartnerWinning = winnerPos == myPartnerPos;

    if (isPartnerWinning) {
      final isLastPlayer = gameState.tableCards.length == 3;
      final partnerStrength = _getCardStrength(winningTableCard.card, actualMode, trumpSuit);
      final isStrong = partnerStrength >= (actualMode == GameMode.sun ? 8 : 20);

      if (isLastPlayer || isStrong) {
        final ten = moves.firstWhere(
            (m) => m.card.rank == Rank.ten && !m.isTrump,
            orElse: () => _MoveCandidate(card: moves[0].card, idx: -1, strength: 0, points: 0, isTrump: false)
        );
        if (ten.idx != -1) {
          return HintResult(
            action: 'PLAY',
            cardIndex: ten.idx,
            reasoning: 'شريكك فايز — ارمي العشرة (${ten.card.rank.symbol}${_suitLabel(ten.card.suit)})',
          );
        }

        final pointCards = [...moves]..sort((a, b) => b.points.compareTo(a.points));
        final best = pointCards[0];
        return HintResult(
          action: 'PLAY',
          cardIndex: best.idx,
          reasoning: 'شريكك فايز — ارمي نقاط (${best.card.rank.symbol}${_suitLabel(best.card.suit)})',
        );
      }
    }

    // Try to win
    final winningMoves = moves.where((m) {
      final simTable = [...gameState.tableCards, TableCard(card: m.card, playedBy: playerPos)];
      final newWinner = getTrickWinner(simTable, actualMode, trumpSuit);
      return newWinner == simTable.length - 1;
    }).toList();

    if (winningMoves.isNotEmpty) {
      final cheapest = winningMoves.first;
      return HintResult(
        action: 'PLAY',
        cardIndex: cheapest.idx,
        reasoning: 'اكسب اللفة بـ ${cheapest.card.rank.symbol}${_suitLabel(cheapest.card.suit)}',
      );
    }

    // Can't win - play lowest
    final lowPointMoves = moves.where((m) => m.points == 0).toList();
    if (lowPointMoves.isNotEmpty) {
      final lowest = lowPointMoves.first;
      return HintResult(
        action: 'PLAY',
        cardIndex: lowest.idx,
        reasoning: 'ما تقدر تفوز — ارمي أقل ورقة (${lowest.card.rank.symbol}${_suitLabel(lowest.card.suit)})',
      );
    }

    final lowest = moves.first;
    return HintResult(
      action: 'PLAY',
      cardIndex: lowest.idx,
      reasoning: 'ما تقدر تفوز — ارمي أقل ورقة (${lowest.card.rank.symbol}${_suitLabel(lowest.card.suit)})',
    );
  }
}

class _MoveCandidate {
  final CardModel card;
  final int idx;
  final int strength;
  final int points;
  final bool isTrump;

  _MoveCandidate({
    required this.card,
    required this.idx,
    required this.strength,
    required this.points,
    required this.isTrump,
  });
}
