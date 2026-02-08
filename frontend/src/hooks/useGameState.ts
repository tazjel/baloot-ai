import { useState, useEffect, useRef, useCallback } from 'react';
import { GameState, GamePhase, PlayerPosition, DoublingLevel, UserProfile, DeclaredProject, Suit, Rank, RoundResult, DetailedScore } from '../types';
import { AccountingEngine } from '../services/AccountingEngine';
import { generateDeck, isValidMove, getTrickWinner, POINT_VALUES, detectProjects, calculateFinalScore, getProjectScoreValue, sortHand, resolveProjectConflicts } from '../utils/gameLogic';
import { AVATARS } from '../constants';

// Import our new hooks
import { useGameSocket } from './useGameSocket';
import { useGameAudio } from './useGameAudio';
import { useLocalBot } from './useLocalBot';

const INITIAL_GAME_STATE: GameState = {
    players: [
        { position: PlayerPosition.Bottom, name: 'أنا', avatar: AVATARS.ME, hand: [], score: 0, isDealer: false, isActive: true, index: 0 },
        { position: PlayerPosition.Right, name: 'سالم', avatar: AVATARS.RIGHT, hand: [], score: 0, isDealer: false, isActive: false, index: 1 },
        { position: PlayerPosition.Top, name: 'شريكي', avatar: AVATARS.TOP, hand: [], score: 0, isDealer: false, isActive: false, index: 2 },
        { position: PlayerPosition.Left, name: 'عمر', avatar: AVATARS.LEFT, hand: [], score: 0, isDealer: true, isActive: false, index: 3 },
    ],
    currentTurnIndex: 0,
    phase: GamePhase.Waiting,
    tableCards: [],
    bid: { type: null, suit: null, bidder: null, doubled: false },
    teamScores: { us: 0, them: 0 },
    floorCard: null,
    dealerIndex: 3,
    biddingRound: 1,
    declarations: {},
    doublingLevel: DoublingLevel.NORMAL,
    isLocked: false,
    matchScores: { us: 0, them: 0 },
    roundHistory: [],
    deck: [],
    settings: { turnDuration: 99999, strictMode: false, soundEnabled: true, gameSpeed: 'NORMAL', cardLanguage: 'EN' },
    lastTrick: null
};

export const useGameState = () => {
    // ===== CORE STATE =====
    const [gameState, setGameState] = useState<GameState>(INITIAL_GAME_STATE);
    const [messages, setMessages] = useState<{ sender: string, text: string }[]>([]);
    const [userProfile, setUserProfile] = useState<UserProfile>(() => {
        const saved = localStorage.getItem('baloot_user_profile');
        return saved ? JSON.parse(saved) : { tier: 'Bronze', leaguePoints: 0, level: 1, xp: 0, xpToNextLevel: 1000, coins: 0 };
    });
    const [isCuttingDeck, setIsCuttingDeck] = useState(false);
    const turnStartTimeRef = useRef<number>(0);

    // ===== COMPOSED HOOKS =====
    const socket = useGameSocket();
    const audio = useGameAudio(gameState);
    const bot = useLocalBot({
        gameState,
        roomId: socket.roomId,
        isCuttingDeck,
        onBotAction: (playerIndex, action, payload) => {
            if (gameState.phase === GamePhase.Bidding) {
                handleBiddingAction(playerIndex, action, payload);
            } else if (action === 'PLAY') {
                handleCardPlay(playerIndex, payload.cardIndex);
            }
        }
    });

    // ===== SOCKET INTEGRATION =====
    // Listen for game updates from server
    useEffect(() => {
        socket.onGameUpdate((newState) => {
            setGameState(prev => ({ ...newState, settings: prev.settings }));
        });
    }, [socket]);

    // ===== USER PROFILE PERSISTENCE =====
    useEffect(() => {
        localStorage.setItem('baloot_user_profile', JSON.stringify(userProfile));
    }, [userProfile]);

    // ===== HELPERS =====
    const addSystemMessage = useCallback((text: string) => {
        setMessages(prev => [...prev, { sender: "النظام", text }]);
    }, []);

    // ===== GAME LOGIC =====

    const startNewRound = useCallback((nextDealerIndex: number = 3, matchScores = gameState.matchScores, newSettings?: any) => {
        setIsCuttingDeck(true);
        setTimeout(() => {
            setIsCuttingDeck(false);
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
            const dealerName = INITIAL_GAME_STATE.players[safeDealerIdx]?.name || 'Unknown';
            addSystemMessage(`تم قص الورق (سقا) - الموزع: ${dealerName}`);
            addSystemMessage(`بدأت الجولة`);
        }, 800);

        turnStartTimeRef.current = performance.now();
    }, [gameState.matchScores, addSystemMessage]);

    // --- TURN TIMER ENFORCEMENT ---
    useEffect(() => {
        if (gameState.currentTurnIndex !== 0) return;
        if (gameState.phase !== GamePhase.Bidding && gameState.phase !== GamePhase.Playing) return;
        if (gameState.settings.turnDuration > 100) return;
        if (socket.roomId) return; // Server is authority

        const timer = setTimeout(() => {
            addSystemMessage("انتهى الوقت! (Time's Up)");
            if (gameState.phase === GamePhase.Bidding) {
                handleBiddingAction(0, 'PASS');
            } else {
                const hand = gameState.players[0].hand;
                let trumpSuit = gameState.bid.type === 'HOKUM' ? (gameState.bid.suit || null) : null;
                const mode = gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';

                if (gameState.bid.type === 'HOKUM' && !trumpSuit) trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;

                const validIndex = hand.findIndex(c => isValidMove(c, hand, gameState.tableCards, mode, trumpSuit, gameState.isLocked));
                const playIndex = validIndex !== -1 ? validIndex : 0;

                handleCardPlay(0, playIndex);
            }
        }, gameState.settings.turnDuration * 1000);

        return () => clearTimeout(timer);
    }, [gameState.currentTurnIndex, gameState.phase, gameState.settings.turnDuration, socket.roomId]);

    // --- TRICK COMPLETION LOGIC ---
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
    }, [startNewRound]);

    useEffect(() => {
        if (gameState.lastTrick) {
            const timer = setTimeout(() => {
                setGameState(prev => ({ ...prev, lastTrick: null }));
            }, 1000);
            return () => clearTimeout(timer);
        }
    }, [gameState.lastTrick]);

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
    }, [gameState.isProjectRevealing]);

    // --- AKKA EFFECTS ---
    useEffect(() => {
        if (gameState.akkaState) {
            if (gameState.akkaState.claimer !== PlayerPosition.Bottom) {
                audio.playAkkaSound();
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
    }, [gameState.akkaState, audio]);

    // --- CARD PLAY HANDLER ---
    const handleCardPlay = (playerIndex: number, cardIndex: number, metadata?: any) => {
        audio.playCardSound();
        setGameState(prev => {
            if (!prev.players || !prev.players[playerIndex]) return prev;
            const player = prev.players[playerIndex];
            if (!player.hand || cardIndex < 0 || cardIndex >= player.hand.length) return prev;
            const card = player.hand[cardIndex];
            if (!card) return prev;

            const newHand = player.hand.filter((_, i) => i !== cardIndex);
            const newTable = [...prev.tableCards, { card, playedBy: player.position, metadata }];
            const nextIndex = (playerIndex + 1) % 4;

            const newPlayers = prev.players.map((p, idx) => {
                if (idx === playerIndex) return { ...p, hand: newHand, isActive: false, actionText: undefined };
                if (idx === nextIndex && newTable.length < 4) return { ...p, isActive: true };
                return p;
            });

            if (newTable.length === 4) {
                return {
                    ...prev,
                    players: newPlayers,
                    tableCards: newTable,
                    isTrickTransitioning: true
                };
            }

            const now = performance.now();
            const duration = (now - turnStartTimeRef.current).toFixed(2);

            const nextPlayer = newPlayers[nextIndex];
            // @ts-ignore
            import('../utils/devLogger').then(({ devLogger }) => {
                devLogger.log('PERF', `Turn Complete (Play): ${player.name}`, { duration: `${duration}ms` });
                if (socket.roomId && nextPlayer.index !== 0) {
                    devLogger.log('PERF', `Waiting for Remote Player: ${nextPlayer.name} (Bot? ${nextPlayer.isBot})`);
                }
            });
            turnStartTimeRef.current = now;

            return { ...prev, players: newPlayers, tableCards: newTable, currentTurnIndex: nextIndex };
        });
    };

    // --- BIDDING HANDLER ---
    const handleBiddingAction = (playerIndex: number, action: string, payload?: any) => {
        const speechText = action === 'PASS' ? 'Bass' : action === 'SUN' ? 'Sun' : action === 'HOKUM' ? 'Hokum' : action;
        audio.speakAction(speechText);

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
                        setTimeout(() => startNewRound((dealerIdx + 1) % 4, prev.matchScores), 1500);
                        return prev;
                    }
                }
            } else {
                let pickupIndex = playerIndex;
                if (action === 'ASHKAL') {
                    action = 'SUN';
                    pickupIndex = (playerIndex + 2) % 4;
                    newPlayers[playerIndex].actionText = 'أشكال';
                }

                let selectedSuit: Suit | null = null;
                if (action === 'HOKUM') {
                    if (prev.biddingRound === 1 && prev.floorCard) selectedSuit = prev.floorCard.suit;
                    else if (prev.biddingRound === 2 && payload?.suit) selectedSuit = payload.suit;
                    else selectedSuit = Suit.Spades;
                }

                newBid = { type: action as any, suit: selectedSuit, bidder: newPlayers[playerIndex].position, doubled: false };
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
                    const mode = action === 'SUN' ? 'SUN' : 'HOKUM';
                    p.hand = sortHand(p.hand, mode, selectedSuit);
                });

                addSystemMessage(`${newPlayers[playerIndex].name} اشترى ${action === 'SUN' ? 'صن' : 'حكم'}`);
                newPhase = GamePhase.Playing;

                const isSun = action === 'SUN';
                let trumpSuit = isSun ? null : (prev.floorCard?.suit || null);
                const newDeclarations: any = {};
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
            // @ts-ignore
            import('../utils/devLogger').then(({ devLogger }) => {
                devLogger.log('PERF', `Turn Complete (Bidding): ${prev.players[playerIndex].name}`, { duration: `${duration}ms` });
            });
            turnStartTimeRef.current = now;

            return { ...prev, players: newPlayers, currentTurnIndex: nextIndex, biddingRound: newRound };
        });
    };

    // --- DOUBLING HANDLER ---
    const handleDoublingAction = (playerIndex: number) => {
        setGameState(prev => {
            let newLevel = prev.doublingLevel;
            if (newLevel === DoublingLevel.NORMAL) newLevel = DoublingLevel.DOUBLE;
            else if (newLevel === DoublingLevel.DOUBLE) newLevel = DoublingLevel.TRIPLE;

            addSystemMessage(`${prev.players[playerIndex].name} رفع المشاريع`);
            audio.speakAction(newLevel === DoublingLevel.DOUBLE ? 'Sra' : 'Triple');

            return { ...prev, doublingLevel: newLevel, isLocked: prev.bid.type === 'HOKUM' };
        });
    };

    // --- MAIN ACTION DISPATCHER ---
    const handlePlayerAction = (action: string, payload?: any) => {
        // Block duplicates except Qayd escape hatch
        if (socket.isSendingAction && action !== 'QAYD_CANCEL' && action !== 'QAYD_CONFIRM') return;

        // @ts-ignore
        import('../utils/devLogger').then(({ devLogger }) => devLogger.log('HOOK', 'Player Action Triggered', { action, payload }));

        // If connected to server, forward action via socket
        if (socket.roomId) {
            socket.sendAction(action, payload, (res: any) => {
                if (!res.success) {
                    addSystemMessage(`Action Failed: ${res.error || 'Unknown'}`);
                    audio.playErrorSound();
                }
            });
            return;
        }

        // --- LEGACY LOCAL LOGIC (Offline) ---
        if (gameState.currentTurnIndex !== 0) return;
        if (gameState.phase === GamePhase.Bidding) {
            handleBiddingAction(0, action, payload);
        } else if (gameState.phase === GamePhase.Playing && action === 'PLAY') {
            const card = gameState.players[0].hand[payload.cardIndex];
            let trumpSuit: Suit | null = null;
            if (gameState.bid.type === 'HOKUM') trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;

            if (!isValidMove(card, gameState.players[0].hand, gameState.tableCards, gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM', trumpSuit, gameState.isLocked)) {
                alert("Invalid Move!");
                return;
            }
            handleCardPlay(0, payload.cardIndex, payload.metadata);
        } else if (action === 'DOUBLE') {
            handleDoublingAction(0);
        }
    };

    // --- FAST FORWARD LOGIC ---
    const handleFastForward = useCallback(() => {
        addSystemMessage(">>> (Fast Forwarding...)");
        setGameState(prev => ({ ...prev, isFastForwarding: true, settings: { ...prev.settings, turnDuration: 0.1 } }));
    }, [addSystemMessage]);

    useEffect(() => {
        if (!gameState.isFastForwarding || gameState.phase !== GamePhase.Playing) return;
        if (gameState.isTrickTransitioning || gameState.isProjectRevealing || gameState.isRoundTransitioning) return;

        const timer = setTimeout(() => {
            const idx = gameState.currentTurnIndex;
            const hand = gameState.players[idx].hand;

            let trumpSuit = gameState.bid.type === 'HOKUM' ? (gameState.bid.suit || null) : null;
            const mode = gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';

            if (gameState.bid.type === 'HOKUM' && !trumpSuit) trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;

            const validIndices = hand.map((c, i) => isValidMove(c, hand, gameState.tableCards, mode, trumpSuit, gameState.isLocked) ? i : -1).filter(i => i !== -1);

            if (validIndices.length > 0) {
                handleCardPlay(idx, validIndices[0]);
            }
        }, 150);

        return () => clearTimeout(timer);
    }, [gameState.isFastForwarding, gameState.phase, gameState.currentTurnIndex, gameState.tableCards, gameState.isTrickTransitioning]);

    // --- LOGGING EFFECT ---
    useEffect(() => {
        if (!gameState.players || !gameState.players[gameState.currentTurnIndex]) return;
        
        turnStartTimeRef.current = performance.now();
        const player = gameState.players[gameState.currentTurnIndex];
        
        // @ts-ignore
        import('../utils/devLogger').then(({ devLogger }) => {
             devLogger.log('PERF', `New Turn: ${player.name} (Index ${gameState.currentTurnIndex})`);
        });

    }, [gameState.currentTurnIndex]);

    // --- STORE LOGIC ---
    const handlePurchase = (itemId: string, cost: number) => {
        if (userProfile.coins >= cost) {
            setUserProfile(prev => ({ ...prev, coins: prev.coins - cost }));
            audio.playWinSound();
        }
    };

    const calculateFinalScoreExport = calculateFinalScore;

    // ===== PUBLIC API =====
    return {
        gameState,
        setGameState,
        messages,
        userProfile,
        setUserProfile,
        handlePurchase,
        isCuttingDeck,
        isSendingAction: socket.isSendingAction,
        handlePlayerAction,
        handleDebugAction: (action: string, pl?: any) => {
            if (socket.roomId) socket.sendDebugAction(action, pl);
            else if (action === 'TOGGLE_DEBUG') {
                setGameState(prev => ({ ...prev, settings: { ...prev.settings, isDebug: pl.enable, turnDuration: pl.enable ? 99999 : 30 } }));
                addSystemMessage(`Debug Mode: ${pl.enable ? 'ON' : 'OFF'}`);
            }
        },
        updateSettings: (newSettings: any) => {
            setGameState(prev => ({ ...prev, settings: newSettings }));
            if (socket.roomId) {
                socket.sendAction('UPDATE_SETTINGS', newSettings);
            }
        },
        startNewRound,
        addSystemMessage,
        joinGame: socket.joinGame,
        addBot: socket.addBot,
        roomId: socket.roomId,
        handleFastForward,
        isBotThinking: bot.isBotThinking
    };
};
