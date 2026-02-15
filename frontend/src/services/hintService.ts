/**
 * hintService.ts — Synchronous AI hint engine for the human player.
 *
 * Mirrors the heuristic logic from botService.ts but:
 *  - No artificial delay (instant return)
 *  - No IntelligentBot model
 *  - Returns Arabic reasoning strings with each recommendation
 *
 * M17.2: AI Hint System
 */
import { GameState, GamePhase, Suit, CardModel, PlayerPosition, HintResult } from '../types';
import { isValidMove, getTrickWinner } from '../utils/gameLogic';

// ── Constants (duplicated from botService to keep modules independent) ──

const POINTS_SUN: Record<string, number> = {
    'A': 11, '10': 10, 'K': 4, 'Q': 3, 'J': 2, '9': 0, '8': 0, '7': 0,
};
const NON_TRUMP_HOKUM: Record<string, number> = {
    'A': 11, '10': 10, 'K': 4, 'Q': 3, 'J': 0, '9': 0, '8': 0, '7': 0,
};
const TRUMP_HOKUM: Record<string, number> = {
    'J': 20, '9': 14, 'A': 11, '10': 10, 'K': 4, 'Q': 3, '8': 0, '7': 0,
};

// ── Helpers ──

const getCardPoints = (card: CardModel, mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number => {
    if (mode === 'SUN') return POINTS_SUN[card.rank] ?? 0;
    if (card.suit === trumpSuit) return TRUMP_HOKUM[card.rank] ?? 0;
    return NON_TRUMP_HOKUM[card.rank] ?? 0;
};

const getCardStrength = (card: CardModel, mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number => {
    if (mode === 'SUN') {
        const order = ['A', '10', 'K', 'Q', 'J', '9', '8', '7'];
        return 8 - order.indexOf(card.rank);
    }
    if (card.suit === trumpSuit) {
        const trumps = ['J', '9', 'A', '10', 'K', 'Q', '8', '7'];
        return 20 + (8 - trumps.indexOf(card.rank));
    }
    const order = ['A', '10', 'K', 'Q', 'J', '9', '8', '7'];
    return 8 - order.indexOf(card.rank);
};

const calculateHandPoints = (hand: CardModel[], type: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number =>
    hand.reduce((total, card) => total + getCardPoints(card, type, trumpSuit), 0);

const getPartnerPos = (myPos: PlayerPosition): PlayerPosition => {
    const map: Record<PlayerPosition, PlayerPosition> = {
        [PlayerPosition.Bottom]: PlayerPosition.Top,
        [PlayerPosition.Top]: PlayerPosition.Bottom,
        [PlayerPosition.Right]: PlayerPosition.Left,
        [PlayerPosition.Left]: PlayerPosition.Right,
    };
    return map[myPos];
};

const SUIT_SYMBOLS: Record<string, string> = {
    '♠': '♠', '♥': '♥', '♦': '♦', '♣': '♣',
};

const suitLabel = (suit: Suit): string => SUIT_SYMBOLS[suit] ?? suit;

// ── Main Entry ──

export function getHint(gameState: GameState): HintResult | null {
    const player = gameState.players[0];
    if (!player) return null;

    if (gameState.phase === GamePhase.Bidding || gameState.biddingPhase === 'GABLAK_WINDOW') {
        return getBiddingHint(gameState, player.hand);
    }
    if (gameState.phase === GamePhase.Playing) {
        return getPlayingHint(gameState, player.hand, player.position);
    }
    return null;
}

// ── Bidding Hint ──

function getBiddingHint(gameState: GameState, hand: CardModel[]): HintResult {
    // 1. Evaluate SUN
    const sunPoints = calculateHandPoints(hand, 'SUN');
    if (sunPoints >= 26) {
        return {
            action: 'SUN',
            reasoning: `يدك قوية بالصن (${sunPoints} نقطة) — اشترِ صن`,
        };
    }

    // 2. ASHKAL (weak SUN)
    if (sunPoints >= 20 && sunPoints < 26) {
        return {
            action: 'ASHKAL',
            reasoning: `صن متوسط (${sunPoints} نقطة) — جرّب أشكال`,
        };
    }

    // 3. Evaluate HOKUM per suit
    const suits = Object.values(Suit);
    const suitsToCheck = gameState.biddingRound === 1 && gameState.floorCard
        ? [gameState.floorCard.suit]
        : gameState.biddingRound === 2
            ? suits.filter(s => gameState.floorCard ? s !== gameState.floorCard.suit : true)
            : [];

    let bestPoints = 0;
    let bestSuit: Suit | null = null;
    let bestHasJack = false;

    for (const s of suitsToCheck) {
        const handToTest = (gameState.biddingRound === 1 && gameState.floorCard)
            ? [...hand, gameState.floorCard]
            : hand;
        const pts = calculateHandPoints(handToTest, 'HOKUM', s);
        const hasJack = handToTest.some(c => c.suit === s && c.rank === 'J');
        const modified = pts + (hasJack ? 10 : 0);

        if (modified > bestPoints) {
            bestPoints = modified;
            bestSuit = s;
            bestHasJack = hasJack;
        }
    }

    if (bestPoints >= 45 && bestSuit) {
        const jackNote = bestHasJack ? ' + الولد' : '';
        return {
            action: 'HOKUM',
            suit: bestSuit,
            reasoning: `حكم ${suitLabel(bestSuit)} — ${bestPoints} نقطة${jackNote}`,
        };
    }

    return {
        action: 'PASS',
        reasoning: `يدك ضعيفة — بس`,
    };
}

// ── Playing Hint ──

interface MoveCandidate {
    card: CardModel;
    idx: number;
    strength: number;
    points: number;
    isTrump: boolean;
}

function getPlayingHint(gameState: GameState, hand: CardModel[], playerPos: PlayerPosition): HintResult {
    const mode: 'SUN' | 'HOKUM' = gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';
    let trumpSuit: Suit | null = null;
    if (mode === 'HOKUM') trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;

    // Build valid moves
    const moves: MoveCandidate[] = hand
        .map((card, idx) => ({
            card,
            idx,
            strength: getCardStrength(card, mode, trumpSuit),
            points: getCardPoints(card, mode, trumpSuit),
            isTrump: mode === 'HOKUM' && card.suit === trumpSuit,
        }))
        .filter(m => isValidMove(m.card, hand, gameState.tableCards, mode, trumpSuit, gameState.isLocked));

    if (moves.length === 0) {
        return { action: 'PLAY', cardIndex: 0, reasoning: 'العب أي ورقة' };
    }

    if (moves.length === 1) {
        return {
            action: 'PLAY',
            cardIndex: moves[0].idx,
            reasoning: `ورقة واحدة متاحة — ${moves[0].card.rank}${suitLabel(moves[0].card.suit)}`,
        };
    }

    // Sort by strength (ascending — weakest first)
    moves.sort((a, b) => a.strength - b.strength);

    const myPartnerPos = getPartnerPos(playerPos);
    const didIBuy = gameState.bid.bidder === playerPos;

    // ── Leading (table empty) ──
    if (gameState.tableCards.length === 0) {
        // HOKUM: buyer leads trump
        if (mode === 'HOKUM' && didIBuy && trumpSuit) {
            const trumpMoves = moves.filter(m => m.isTrump);
            if (trumpMoves.length > 0) {
                const best = trumpMoves[trumpMoves.length - 1];
                return {
                    action: 'PLAY',
                    cardIndex: best.idx,
                    reasoning: `إبدأ بالحكم — اسحب أوراق الخصم (${best.card.rank}${suitLabel(best.card.suit)})`,
                };
            }
        }
        // SUN: lead Ace if available
        if (mode === 'SUN') {
            const aces = moves.filter(m => m.card.rank === 'A');
            if (aces.length > 0) {
                return {
                    action: 'PLAY',
                    cardIndex: aces[0].idx,
                    reasoning: `إبدأ بالأكة — ورقة مضمونة (${aces[0].card.rank}${suitLabel(aces[0].card.suit)})`,
                };
            }
            // Strongest card
            const strongest = moves[moves.length - 1];
            return {
                action: 'PLAY',
                cardIndex: strongest.idx,
                reasoning: `إبدأ بأقوى ورقة (${strongest.card.rank}${suitLabel(strongest.card.suit)})`,
            };
        }
        // Default: strongest
        const strongest = moves[moves.length - 1];
        return {
            action: 'PLAY',
            cardIndex: strongest.idx,
            reasoning: `إبدأ بأقوى ورقة (${strongest.card.rank}${suitLabel(strongest.card.suit)})`,
        };
    }

    // ── Following ──
    const winIdx = getTrickWinner(gameState.tableCards, mode, trumpSuit);
    const winningCard = gameState.tableCards[winIdx];
    const winnerPos = winningCard.playedBy;
    const isPartnerWinning = winnerPos === myPartnerPos;

    // Partner winning — dump points
    if (isPartnerWinning) {
        const isLastPlayer = gameState.tableCards.length === 3;
        const partnerStrength = getCardStrength(winningCard.card, mode, trumpSuit);
        const isStrong = partnerStrength >= (mode === 'SUN' ? 8 : 20);

        if (isLastPlayer || isStrong) {
            const ten = moves.find(m => m.card.rank === '10' && !m.isTrump);
            if (ten) {
                return {
                    action: 'PLAY',
                    cardIndex: ten.idx,
                    reasoning: `شريكك فايز — ارمي العشرة (${ten.card.rank}${suitLabel(ten.card.suit)})`,
                };
            }
            const pointCards = [...moves].sort((a, b) => b.points - a.points);
            const best = pointCards[0];
            return {
                action: 'PLAY',
                cardIndex: best.idx,
                reasoning: `شريكك فايز — ارمي نقاط (${best.card.rank}${suitLabel(best.card.suit)})`,
            };
        }
    }

    // Try to win the trick
    const winningMoves = moves.filter(m => {
        const simTable = [...gameState.tableCards, { card: m.card, playedBy: playerPos }];
        const newWinner = getTrickWinner(simTable, mode, trumpSuit);
        return newWinner === simTable.length - 1;
    });

    if (winningMoves.length > 0) {
        // Win with cheapest winning card
        const cheapest = winningMoves[0];
        return {
            action: 'PLAY',
            cardIndex: cheapest.idx,
            reasoning: `اكسب اللفة بـ ${cheapest.card.rank}${suitLabel(cheapest.card.suit)}`,
        };
    }

    // Can't win — play lowest
    const lowPointMoves = moves.filter(m => m.points === 0);
    if (lowPointMoves.length > 0) {
        const lowest = lowPointMoves[0];
        return {
            action: 'PLAY',
            cardIndex: lowest.idx,
            reasoning: `ما تقدر تفوز — ارمي أقل ورقة (${lowest.card.rank}${suitLabel(lowest.card.suit)})`,
        };
    }

    const lowest = moves[0];
    return {
        action: 'PLAY',
        cardIndex: lowest.idx,
        reasoning: `ما تقدر تفوز — ارمي أقل ورقة (${lowest.card.rank}${suitLabel(lowest.card.suit)})`,
    };
}
