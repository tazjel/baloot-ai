import { GameState, PlayerPosition, GamePhase, CardModel, Suit, Rank } from "../types";
import { isValidMove, getTrickWinner } from "../utils/gameLogic";

// --- CONSTANTS ---
const POINTS_SUN: Record<string, number> = { 'A': 11, '10': 10, 'K': 4, 'Q': 3, 'J': 2, '9': 0, '8': 0, '7': 0 };
const NON_TRUMP_HOKUM = { 'A': 11, '10': 10, 'K': 4, 'Q': 3, 'J': 0, '9': 0, '8': 0, '7': 0 };
const TRUMP_HOKUM = { 'J': 20, '9': 14, 'A': 11, '10': 10, 'K': 4, 'Q': 3, '8': 0, '7': 0 };

// --- HELPERS ---

const getCardPoints = (card: CardModel, mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number => {
    if (mode === 'SUN') return POINTS_SUN[card.rank];
    if (card.suit === trumpSuit) return TRUMP_HOKUM[card.rank] || 0;
    return NON_TRUMP_HOKUM[card.rank] || 0;
};

// Strength: Higher is better. Used for "Can I win?" and "Save high cards".
const getCardStrength = (card: CardModel, mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number => {
    if (mode === 'SUN') {
        const order = ['A', '10', 'K', 'Q', 'J', '9', '8', '7'];
        return 8 - order.indexOf(card.rank); // 8=Ace, 1=7
    } else {
        if (card.suit === trumpSuit) {
            const trumps = ['J', '9', 'A', '10', 'K', 'Q', '8', '7'];
            return 20 + (8 - trumps.indexOf(card.rank)); // 28=J, 21=7
        }
        const order = ['A', '10', 'K', 'Q', 'J', '9', '8', '7'];
        return 8 - order.indexOf(card.rank);
    }
};

const calculateHandPoints = (hand: CardModel[], type: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number => {
    return hand.reduce((total, card) => total + getCardPoints(card, type, trumpSuit), 0);
};

const getPartnerPos = (myPos: PlayerPosition): PlayerPosition => {
    const map = {
        [PlayerPosition.Bottom]: PlayerPosition.Top,
        [PlayerPosition.Top]: PlayerPosition.Bottom,
        [PlayerPosition.Right]: PlayerPosition.Left,
        [PlayerPosition.Left]: PlayerPosition.Right
    };
    return map[myPos];
};

// --- CORE LOGIC ---
import { IntelligentBot } from "../ai/IntelligentBot";
import { devLogger } from '../utils/devLogger';

// --- SINGLETON BOT INSTANCE ---
const intelligentBot = new IntelligentBot();
let isModelLoading = false;

// Ensure model is loaded
const ensureBotLoaded = async () => {
    if (!intelligentBot.session && !isModelLoading) {
        isModelLoading = true;
        devLogger.log('BOT_SVC', "Loading IntelligentBot model...");
        await intelligentBot.loadModel();
        isModelLoading = false;
    }
};

// Start loading immediately (lazy load)
ensureBotLoaded();

export const getBotDecision = async (gameState: GameState, playerPos: PlayerPosition): Promise<{ action: string, cardIndex?: number, suit?: Suit }> => {
    // Artificial Delay for realism
    const delay = 800 + Math.random() * 800;
    devLogger.log('BOT_PERF', `Simulated Thinking Delay: ${delay.toFixed(0)}ms`);
    await new Promise(resolve => setTimeout(resolve, delay));

    const startThink = performance.now();

    const playerIndex = gameState.players.findIndex(p => p.position === playerPos);
    const player = gameState.players[playerIndex];
    if (!player) return { action: 'PASS' };

    devLogger.log('BOT_DECISION', `Thinking for ${playerPos}...`, { phase: gameState.phase, handSize: player.hand.length });

    // ================= BIDDING PHASE =================
    if (gameState.phase === GamePhase.Bidding) {
        // ... Heuristic Bidding ...
        // (Logging truncated for brevity, but let's log the final decision)

        // 1. Evaluate SUN
        const sunPoints = calculateHandPoints(player.hand, 'SUN');
        if (sunPoints >= 26) {
            devLogger.log('BOT_BID', `${playerPos} bids SUN`, { points: sunPoints });
            return { action: 'SUN' };
        }

        // 2. Ashkal
        if (sunPoints >= 20 && sunPoints < 26) {
            devLogger.log('BOT_BID', `${playerPos} bids ASHKAL`, { points: sunPoints });
            return { action: 'ASHKAL' };
        }

        // 3. Evaluate HOKUM
        let bestHokumPoints = 0;
        let bestSuit: Suit | null = null;
        const suits = Object.values(Suit);
        const suitsToCheck = gameState.biddingRound === 1 && gameState.floorCard ? [gameState.floorCard.suit] : (gameState.biddingRound === 2 ? suits : []);

        for (const s of suitsToCheck) {
            if (gameState.biddingRound === 2 && gameState.floorCard && s === gameState.floorCard.suit) continue;
            const handToTest = (gameState.biddingRound === 1 && gameState.floorCard) ? [...player.hand, gameState.floorCard] : player.hand;
            const p = calculateHandPoints(handToTest, 'HOKUM', s);
            const hasJack = handToTest.some(c => c.suit === s && c.rank === 'J');
            const modifiedPoints = p + (hasJack ? 10 : 0);

            if (modifiedPoints > bestHokumPoints) {
                bestHokumPoints = modifiedPoints;
                bestSuit = s;
            }
        }

        if (bestHokumPoints >= 45) {
            devLogger.log('BOT_BID', `${playerPos} bids HOKUM`, { suit: bestSuit, points: bestHokumPoints });
            return { action: 'HOKUM', suit: bestSuit || undefined };
        }

        devLogger.log('BOT_BID', `${playerPos} passes`);
        return { action: 'PASS' };
    }

    // ================= PLAYING PHASE =================
    if (gameState.phase === GamePhase.Playing) {
        const mode = gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';
        let trumpSuit: Suit | null = null;
        if (mode === 'HOKUM') trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;

        // Valid Moves for fallback/validation
        const moves = player.hand.map((card, idx) => ({
            card, idx,
            strength: getCardStrength(card, mode, trumpSuit),
            points: getCardPoints(card, mode, trumpSuit),
            isTrump: mode === 'HOKUM' && card.suit === trumpSuit
        })).filter(m => isValidMove(m.card, player.hand, gameState.tableCards, mode, trumpSuit, gameState.isLocked));

        if (moves.length === 0) {
            devLogger.error('BOT_PLAY', "No valid moves found!", { hand: player.hand });
            return { action: 'PLAY', cardIndex: 0 };
        }

        // --- INTELLIGENT BOT PREDICTION ---
        try {
            await ensureBotLoaded(); // Ensure model is ready

            if (intelligentBot.session) {
                // devLogger.log('BOT_AI', `Querying Brain for ${playerPos}...`);
                const startTime = performance.now();

                const predictedIndex = await intelligentBot.predict(gameState, playerIndex);

                const endTime = performance.now();
                // devLogger.log('BOT_AI', `IntelligentBot responded in ${(endTime - startTime).toFixed(2)}ms. Prediction: Index ${predictedIndex}`);

                if (predictedIndex !== -1) {
                    // Validate prediction is a valid move
                    // We need to map hand index to one of the 'valid moves' we calculated? 
                    // Or just check if predicted card is in the valid moves list.

                    // predictedIndex is index in 'player.hand'.
                    const predictedCard = player.hand[predictedIndex];
                    if (predictedCard) {
                        const isValid = moves.some(m => m.card.id === predictedCard.id);
                        if (isValid) {
                            devLogger.success('BOT_AI', `Brain Chose: ${predictedCard.rank}${predictedCard.suit}`, { index: predictedIndex });
                            return { action: 'PLAY', cardIndex: predictedIndex };
                        } else {
                            devLogger.warn('BOT_AI', `Illegal Move Suggested: ${predictedCard.rank}${predictedCard.suit}. Fallback.`, { validMoves: moves.map(m => m.card.rank + m.card.suit) });
                        }
                    } else {
                        devLogger.warn('BOT_AI', `Invalid Index: ${predictedIndex}`);
                    }
                }
            } else {
                devLogger.warn('BOT_AI', "Session null. Using Heuristic.");
            }
        } catch (e) {
            devLogger.error('BOT_AI', "Error", e);
        }

        // --- HEURISTIC FALLBACK (Existing Logic) ---
        devLogger.log('BOT_HEURISTIC', "Fallback Triggered");

        // Sort moves by Strength
        moves.sort((a, b) => a.strength - b.strength);

        // We need to return specific logic results like before
        // Simulating the exact return paths from previous code but logging result

        const bestHeuristicMove = (() => {
            const myPartnerPos = getPartnerPos(playerPos);
            const didIBuy = gameState.bid.bidder === playerPos;
            // const didPartnerBuy = gameState.bid.bidder === myPartnerPos; // Unused
            // const didWeBuy = didIBuy || didPartnerBuy; // Unused

            // Scenario A: Leading
            if (gameState.tableCards.length === 0) {
                if (mode === 'HOKUM' && didIBuy && trumpSuit) {
                    const trumps = moves.filter(m => m.isTrump);
                    if (trumps.length > 0) return trumps[trumps.length - 1];
                }
                if (mode === 'SUN') {
                    const aces = moves.filter(m => m.card.rank === 'A');
                    if (aces.length > 0) return aces[0];
                    return moves[moves.length - 1];
                }
                return moves[moves.length - 1];
            }

            // Scenario B: Following
            const winIdx = getTrickWinner(gameState.tableCards, mode, trumpSuit);
            const winningCard = gameState.tableCards[winIdx];
            const winnerPos = winningCard.playedBy;
            const isPartnerWinning = winnerPos === myPartnerPos;

            if (isPartnerWinning) {
                const isLastPlayer = gameState.tableCards.length === 3;
                const partnerStrength = getCardStrength(winningCard.card, mode, trumpSuit);
                const isStrong = partnerStrength >= (mode === 'SUN' ? 8 : 20);

                if (isLastPlayer || isStrong) {
                    const ten = moves.find(m => m.card.rank === '10' && !m.isTrump);
                    if (ten) return ten;
                    const pointCards = [...moves].sort((a, b) => b.points - a.points);
                    return pointCards[0];
                }
            }

            const winningMoves = moves.filter(m => {
                const simTable = [...gameState.tableCards, { card: m.card, playedBy: playerPos }];
                const newWinner = getTrickWinner(simTable, mode, trumpSuit);
                return newWinner === simTable.length - 1;
            });

            if (winningMoves.length > 0) return winningMoves[0];

            const lowPointMoves = moves.filter(m => m.points === 0);
            if (lowPointMoves.length > 0) return lowPointMoves[0];

            return moves[0];
        })();

        devLogger.log('BOT_HEURISTIC', `Selected: ${bestHeuristicMove.card.rank}${bestHeuristicMove.card.suit}`, {
            duration: `${(performance.now() - startThink).toFixed(2)}ms`
        });
        return { action: 'PLAY', cardIndex: bestHeuristicMove.idx };
    }

    return { action: 'PASS' };
};
