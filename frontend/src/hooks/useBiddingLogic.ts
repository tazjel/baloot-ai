import { useEffect, useRef } from 'react';
import { GameState, GamePhase, PlayerPosition, Suit, DeclaredProject } from '../types';
import { detectProjects, sortHand } from '../utils/gameLogic';
import { soundManager } from '../services/SoundManager';

interface UseBiddingLogicArgs {
    gameState: GameState;
    setGameState: React.Dispatch<React.SetStateAction<GameState>>;
    addSystemMessage: (text: string) => void;
    speakAction: (text: string) => void;
    startNewRound: (nextDealerIndex: number, matchScores?: { us: number; them: number }) => void;
    turnStartTimeRef: React.MutableRefObject<number>;
}

export const useBiddingLogic = ({
    gameState,
    setGameState,
    addSystemMessage,
    speakAction,
    startNewRound,
    turnStartTimeRef,
}: UseBiddingLogicArgs) => {
    const redealTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Cleanup redeal timer on unmount
    useEffect(() => {
        return () => {
            if (redealTimerRef.current) {
                clearTimeout(redealTimerRef.current);
                redealTimerRef.current = null;
            }
        };
    }, []);

    const handleBiddingAction = (playerIndex: number, action: string, payload?: any) => {
        const speechText = action === 'PASS' ? 'Bass' : action === 'SUN' ? 'Sun' : action === 'HOKUM' ? 'Hokum' : action;
        speakAction(speechText);

        // M18: Bid sounds
        if (action === 'PASS') soundManager.playPassSound();
        else if (action === 'SUN' || action === 'ASHKAL') soundManager.playSunSound();
        else if (action === 'HOKUM') soundManager.playHokumSound();

        setGameState(prev => {
            if (!prev.players[playerIndex].isActive) return prev;

            const newPlayers = prev.players.map(p => ({ ...p, hand: [...p.hand] }));
            newPlayers[playerIndex].actionText = action === 'PASS' ? 'بس' : action === 'SUN' ? 'صن' : action === 'HOKUM' ? 'حكم' : action;
            newPlayers[playerIndex].isActive = false;

            let nextIndex = (playerIndex + 1) % 4;
            let newBid = { ...prev.bid };
            let newPhase = prev.phase;
            let newRound = prev.biddingRound;
            const dealerIdx = prev.dealerIndex;
            const firstBidderIdx = (dealerIdx + 1) % 4;

            if (action === 'PASS') {
                if (nextIndex === firstBidderIdx) {
                    if (prev.biddingRound === 1) {
                        newRound = 2;
                        addSystemMessage("الجولة الثانية من الشراء");
                    } else {
                        addSystemMessage("Gash! Everyone passed. Redealing...");
                        if (redealTimerRef.current) clearTimeout(redealTimerRef.current);
                        const scores = prev.matchScores;
                        redealTimerRef.current = setTimeout(() => {
                            redealTimerRef.current = null;
                            startNewRound((dealerIdx + 1) % 4, scores);
                        }, 1500);
                        return prev;
                    }
                }
            } else {
                let actualAction = action;
                let pickupIndex = playerIndex;
                if (action === 'ASHKAL') {
                    actualAction = 'SUN';
                    pickupIndex = (playerIndex + 2) % 4;
                    newPlayers[playerIndex].actionText = 'أشكال';
                }

                let selectedSuit: Suit | null = null;
                if (actualAction === 'HOKUM') {
                    if (prev.biddingRound === 1 && prev.floorCard) selectedSuit = prev.floorCard.suit;
                    else if (prev.biddingRound === 2 && payload?.suit) selectedSuit = payload.suit as Suit;
                    else selectedSuit = Suit.Spades;
                }

                newBid = { type: actualAction as 'SUN' | 'HOKUM', suit: selectedSuit, bidder: newPlayers[playerIndex].position, doubled: false };
                if (prev.floorCard) newPlayers[pickupIndex].hand.push(prev.floorCard);

                const remainingDeck = prev.deck.slice(21);
                let deckPointer = 0;
                for (let i = 0; i < 4; i++) {
                    const pIdx = (dealerIdx + 1 + i) % 4;
                    const count = (pIdx === pickupIndex) ? 2 : 3;
                    for (let k = 0; k < count && deckPointer < remainingDeck.length; k++) {
                        newPlayers[pIdx].hand.push(remainingDeck[deckPointer++]);
                    }
                }

                newPlayers.forEach(p => {
                    const mode = actualAction === 'SUN' ? 'SUN' : 'HOKUM';
                    p.hand = sortHand(p.hand, mode, selectedSuit);
                });

                addSystemMessage(`${newPlayers[playerIndex].name} اشترى ${actualAction === 'SUN' ? 'صن' : 'حكم'}`);
                newPhase = GamePhase.Playing;

                const isSun = actualAction === 'SUN';
                const trumpSuit = isSun ? null : (prev.floorCard?.suit || null);
                const newDeclarations: { [key: string]: DeclaredProject[] } = {};
                let hasAnyProjects = false;
                newPlayers.forEach(p => {
                    newDeclarations[p.position] = detectProjects(p.hand, p.position, trumpSuit);
                    if (newDeclarations[p.position].length > 0) hasAnyProjects = true;
                });

                nextIndex = (dealerIdx + 1) % 4;
                newPlayers.forEach(p => p.isActive = false);
                newPlayers[nextIndex].isActive = true;

                return {
                    ...prev,
                    players: newPlayers,
                    currentTurnIndex: nextIndex,
                    bid: newBid,
                    phase: newPhase,
                    biddingRound: newRound,
                    declarations: newDeclarations,
                    isProjectRevealing: hasAnyProjects,
                    floorCard: null
                };
            }

            newPlayers[nextIndex].isActive = true;

            const now = performance.now();
            const duration = (now - turnStartTimeRef.current).toFixed(2);
            // @ts-ignore - dynamic import for dev logger
            import('../utils/devLogger').then(({ devLogger }) => {
                devLogger.log('PERF', `Turn Complete (Bidding): ${prev.players[playerIndex].name}`, { duration: `${duration}ms` });
            });
            turnStartTimeRef.current = now;

            return { ...prev, players: newPlayers, currentTurnIndex: nextIndex, biddingRound: newRound };
        });
    };

    return { handleBiddingAction };
};
