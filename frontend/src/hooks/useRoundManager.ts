import { useCallback, useEffect, useRef } from 'react';
import { GameState, GamePhase, PlayerPosition, DoublingLevel, DeclaredProject, DetailedScore, RoundResult, Suit } from '../types';
import { AccountingEngine } from '../services/AccountingEngine';
import { generateDeck, getTrickWinner, POINT_VALUES, detectProjects, getProjectScoreValue, sortHand, resolveProjectConflicts } from '../utils/gameLogic';
import { AVATARS, INITIAL_PLAYERS } from '../constants';

interface UseRoundManagerArgs {
    gameState: GameState;
    setGameState: React.Dispatch<React.SetStateAction<GameState>>;
    addSystemMessage: (text: string) => void;
    playAkkaSound: () => void;
}


export const useRoundManager = ({
    gameState,
    setGameState,
    addSystemMessage,
    playAkkaSound,
}: UseRoundManagerArgs) => {
    const isCuttingDeckRef = useRef(false);
    const [isCuttingDeck, setIsCuttingDeckState] = [
        isCuttingDeckRef.current,
        (val: boolean) => { isCuttingDeckRef.current = val; }
    ];

    // We need a state-based isCuttingDeck for re-renders
    const [isCuttingDeckState, setIsCuttingDeck] = [
        false as boolean,
        (() => {}) as React.Dispatch<React.SetStateAction<boolean>>
    ];

    // --- START NEW ROUND ---
    const startNewRound = useCallback((nextDealerIndex: number = 3, matchScores = gameState.matchScores, newSettings?: any) => {
        // Cutting deck animation handled by parent via isCuttingDeck state
        const deck = generateDeck();

        const p1Hand = sortHand(deck.slice(0, 5), 'HOKUM', null);
        const p2Hand = sortHand(deck.slice(5, 10), 'HOKUM', null);
        const p3Hand = sortHand(deck.slice(10, 15), 'HOKUM', null);
        const p4Hand = sortHand(deck.slice(15, 20), 'HOKUM', null);
        const floor = deck[20];
        const firstTurn = (nextDealerIndex + 1) % 4;

        setGameState(prev => ({
            ...prev,
            matchScores,
            phase: GamePhase.Bidding,
            currentTurnIndex: firstTurn,
            dealerIndex: nextDealerIndex,
            biddingRound: 1,
            floorCard: floor,
            tableCards: [],
            deck,
            bid: { type: null, suit: null, bidder: null, doubled: false },
            declarations: {},
            doublingLevel: DoublingLevel.NORMAL,
            roundHistory: prev.roundHistory || [],
            isLocked: false,
            isRoundTransitioning: false,
            isTrickTransitioning: false,
            isProjectRevealing: false,
            isFastForwarding: false,
            settings: newSettings ? { ...prev.settings, ...newSettings } : prev.settings,
            players: prev.players.map((p, i) => ({
                ...p,
                hand: i === 0 ? p1Hand : i === 1 ? p2Hand : i === 2 ? p3Hand : p4Hand,
                isDealer: i === nextDealerIndex,
                actionText: undefined,
                isActive: i === firstTurn
            }))
        }));

        const safeDealerIdx = (nextDealerIndex >= 0 && nextDealerIndex < 4) ? nextDealerIndex : 0;
        const dealerName = INITIAL_PLAYERS[safeDealerIdx]?.name || 'Unknown';
        addSystemMessage(`تم قص الورق (سقا) - الموزع: ${dealerName}`);
        addSystemMessage(`بدأت الجولة`);
    }, [gameState.matchScores, addSystemMessage, setGameState]);

    // --- TRICK COMPLETION ---
    const completeTrick = useCallback(() => {
        setGameState(prev => {
            if (prev.tableCards.length !== 4) return { ...prev, isTrickTransitioning: false };

            const newTable = prev.tableCards;
            const newPlayers = [...prev.players];

            const trumpSuit = prev.bid.type === 'HOKUM' ? (prev.bid.suit || prev.floorCard?.suit || null) : null;
            const mode = prev.bid.type === 'SUN' ? 'SUN' : 'HOKUM';
            const winIdx = getTrickWinner(newTable, mode, trumpSuit);

            const winnerPos = newTable[winIdx].playedBy;
            const winningPlayerIndex = prev.players.findIndex(p => p.position === winnerPos);
            const isUs = winningPlayerIndex === 0 || winningPlayerIndex === 2;

            let rawTrickPoints = 0;
            newTable.forEach(p => {
                const val = POINT_VALUES[mode][p.card.rank];
                rawTrickPoints += val;
            });

            const isLastTrick = newPlayers.every(p => p.hand.length === 0);
            if (isLastTrick) rawTrickPoints += 10;

            const currentUsRaw = prev.teamScores.us + (isUs ? rawTrickPoints : 0);
            const currentThemRaw = prev.teamScores.them + (!isUs ? rawTrickPoints : 0);

            newPlayers.forEach(p => p.isActive = false);
            newPlayers[winningPlayerIndex].isActive = true;

            if (isLastTrick) {
                const resolvedDeclarations = resolveProjectConflicts(prev.declarations, mode);
                let usProjectPoints = 0;
                let themProjectPoints = 0;

                Object.entries(resolvedDeclarations).forEach(([pos, projects]) => {
                    const isUsPlayer = pos === PlayerPosition.Bottom || pos === PlayerPosition.Top;
                    (projects as DeclaredProject[]).forEach(proj => {
                        const val = getProjectScoreValue(proj.type, mode);
                        if (isUsPlayer) usProjectPoints += val;
                        else themProjectPoints += val;
                    });
                });

                const bidderPos = prev.bid.bidder;
                let bidderTeam: 'us' | 'them' | null = null;
                if (bidderPos === PlayerPosition.Bottom || bidderPos === PlayerPosition.Top) bidderTeam = 'us';
                else if (bidderPos === PlayerPosition.Right || bidderPos === PlayerPosition.Left) bidderTeam = 'them';

                const result = AccountingEngine.calculateRoundResult(
                    currentUsRaw,
                    currentThemRaw,
                    usProjectPoints,
                    themProjectPoints,
                    mode,
                    prev.doublingLevel,
                    bidderTeam
                );

                const usDetailed: DetailedScore = {
                    aklat: 0, ardh: 0,
                    mashaari: result.us.projectPoints,
                    abnat: result.us.rawCardPoints,
                    result: result.us.gamePoints,
                    projects: [],
                    gamePoints: result.us.gamePoints
                };
                const themDetailed: DetailedScore = {
                    aklat: 0, ardh: 0,
                    mashaari: result.them.projectPoints,
                    abnat: result.them.rawCardPoints,
                    result: result.them.gamePoints,
                    projects: [],
                    gamePoints: result.them.gamePoints
                };

                const newHistory: RoundResult[] = [...prev.roundHistory, {
                    roundNumber: prev.roundHistory.length + 1,
                    us: usDetailed,
                    them: themDetailed,
                    gameMode: prev.bid.type || undefined,
                    winner: result.winner === 'tie' ? 'tie' : result.winner,
                }];

                const globalUs = prev.matchScores.us + result.us.gamePoints;
                const globalThem = prev.matchScores.them + result.them.gamePoints;

                if (globalUs >= 152 || globalThem >= 152) {
                    return {
                        ...prev,
                        phase: GamePhase.GameOver,
                        matchScores: { us: globalUs, them: globalThem },
                        roundHistory: newHistory,
                        tableCards: [],
                        isTrickTransitioning: false
                    };
                }

                setTimeout(() => startNewRound((prev.dealerIndex + 1) % 4, { us: globalUs, them: globalThem }), 1500);

                return {
                    ...prev,
                    teamScores: { us: currentUsRaw, them: currentThemRaw },
                    matchScores: { us: globalUs, them: globalThem },
                    roundHistory: newHistory,
                    tableCards: [],
                    isRoundTransitioning: true
                };
            }

            const lastTrickData = {
                cards: [...newTable],
                winner: winnerPos
            };

            return {
                ...prev,
                players: newPlayers,
                tableCards: [],
                teamScores: { us: currentUsRaw, them: currentThemRaw },
                currentTurnIndex: winningPlayerIndex,
                isTrickTransitioning: false,
                lastTrick: lastTrickData
            };
        });
    }, [startNewRound, setGameState]);

    // --- TRANSITION EFFECTS ---
    useEffect(() => {
        if (gameState.lastTrick) {
            const timer = setTimeout(() => {
                setGameState(prev => ({ ...prev, lastTrick: null }));
            }, 1000);
            return () => clearTimeout(timer);
        }
    }, [gameState.lastTrick, setGameState]);

    useEffect(() => {
        if (gameState.isTrickTransitioning) {
            const timer = setTimeout(completeTrick, 600);
            return () => clearTimeout(timer);
        }
    }, [gameState.isTrickTransitioning, completeTrick]);

    useEffect(() => {
        if (gameState.isProjectRevealing) {
            const timer = setTimeout(() => {
                setGameState(prev => ({ ...prev, isProjectRevealing: false }));
            }, 800);
            return () => clearTimeout(timer);
        }
    }, [gameState.isProjectRevealing, setGameState]);

    // --- AKKA EFFECTS ---
    useEffect(() => {
        if (gameState.akkaState) {
            if (gameState.akkaState.claimer !== PlayerPosition.Bottom) {
                playAkkaSound();
            }

            setGameState(prev => {
                const claimerIdx = prev.players.findIndex(p => p.position === prev.akkaState?.claimer);
                if (claimerIdx === -1) return prev;

                const newPlayers = [...prev.players];
                newPlayers[claimerIdx] = { ...newPlayers[claimerIdx], actionText: 'AKKA!' };
                return { ...prev, players: newPlayers };
            });

            const timer = setTimeout(() => {
                setGameState(prev => {
                    const claimerIdx = prev.players.findIndex(p => p.position === prev.akkaState?.claimer);
                    if (claimerIdx === -1) return prev;
                    if (prev.players[claimerIdx].actionText === 'AKKA!') {
                        const newPlayers = [...prev.players];
                        newPlayers[claimerIdx] = { ...newPlayers[claimerIdx], actionText: undefined };
                        return { ...prev, players: newPlayers };
                    }
                    return prev;
                });
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [gameState.akkaState, playAkkaSound, setGameState]);

    return {
        startNewRound,
        completeTrick,
    };
};
