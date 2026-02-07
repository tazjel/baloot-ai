import { useState, useEffect, useRef, useCallback } from 'react';
import { GameState, GamePhase, PlayerPosition, DoublingLevel, UserProfile, DeclaredProject, Suit, Rank, RoundResult, DetailedScore } from '../types';
import { AccountingEngine } from '../services/AccountingEngine';
import { generateDeck, isValidMove, getTrickWinner, POINT_VALUES, detectProjects, calculateFinalScore, getProjectScoreValue, sortHand, resolveProjectConflicts } from '../utils/gameLogic';
import { getBotDecision } from '../services/botService';
import socketService from '../services/SocketService';
import { soundManager } from '../services/SoundManager';
import { AVATARS } from '../constants';

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
    const [gameState, setGameState] = useState<GameState>(INITIAL_GAME_STATE);
    const [messages, setMessages] = useState<{ sender: string, text: string }[]>([]);
    const [userProfile, setUserProfile] = useState<UserProfile>(() => {
        const saved = localStorage.getItem('baloot_user_profile');
        return saved ? JSON.parse(saved) : { tier: 'Bronze', leaguePoints: 0, level: 1, xp: 0, xpToNextLevel: 1000, coins: 0 };
    });

    const [roomId, setRoomId] = useState<string | null>(null);
    const [myIndex, setMyIndex] = useState<number>(0);
    const myIndexRef = useRef(0);
    const [isCuttingDeck, setIsCuttingDeck] = useState(false);
    const [isBotThinking, setIsBotThinking] = useState(false);
    const turnStartTimeRef = useRef<number>(0);


    useEffect(() => { myIndexRef.current = myIndex; }, [myIndex]);

    useEffect(() => {
        localStorage.setItem('baloot_user_profile', JSON.stringify(userProfile));
    }, [userProfile]);

    const addSystemMessage = useCallback((text: string) => {
        setMessages(prev => [...prev, { sender: "النظام", text }]);
    }, []);

    const speakAction = useCallback((text: string) => {
        if (!window.speechSynthesis) return;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.volume = 1;
        utterance.rate = 1;
        window.speechSynthesis.speak(utterance);
    }, []);

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
                isFastForwarding: false, // Reset
                settings: newSettings ? { ...prev.settings, ...newSettings } : prev.settings, // Update settings
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
    const [isSendingAction, setIsSendingAction] = useState(false);

    useEffect(() => {
        if (gameState.currentTurnIndex !== 0) return; // Only enforce for Human
        if (gameState.phase !== GamePhase.Bidding && gameState.phase !== GamePhase.Playing) return;
        if (gameState.settings.turnDuration > 100) return; // Disabled if high value

        // If connected to server (roomId exists), DO NOT auto-play locally. 
        // Just show warning. Server is authority.
        if (roomId) return;

        const timer = setTimeout(() => {
            addSystemMessage("انتهى الوقت! (Time's Up)");
            // OFFLINE MODE ONLY: Auto-play
            if (gameState.phase === GamePhase.Bidding) {
                handleBiddingAction(0, 'PASS');
            } else {
                // Play Random Valid Card
                const hand = gameState.players[0].hand;
                let trumpSuit = gameState.bid.type === 'HOKUM' ? (gameState.bid.suit || null) : null;
                const mode = gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';

                // Find first valid card
                if (gameState.bid.type === 'HOKUM' && !trumpSuit) trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;

                const validIndex = hand.findIndex(c => isValidMove(c, hand, gameState.tableCards, mode, trumpSuit, gameState.isLocked));
                const playIndex = validIndex !== -1 ? validIndex : 0;

                handleCardPlay(0, playIndex);
            }
        }, gameState.settings.turnDuration * 1000);

        return () => clearTimeout(timer);
    }, [gameState.currentTurnIndex, gameState.phase, gameState.settings.turnDuration, roomId]);

    // --- TRICK COMPLETION LOGIC ---
    const completeTrick = useCallback(() => {
        setGameState(prev => {
            if (prev.tableCards.length !== 4) return { ...prev, isTrickTransitioning: false };

            const newTable = prev.tableCards;
            const newPlayers = [...prev.players];

            const trumpSuit = prev.bid.type === 'HOKUM' ? (prev.bid.suit || prev.floorCard?.suit || null) : null;
            const mode = prev.bid.type === 'SUN' ? 'SUN' : 'HOKUM';
            const winIdx = getTrickWinner(newTable, mode, trumpSuit);

            soundManager.playWinSound();

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

            // Check Round Over
            if (isLastTrick) {
                // NEW: Resolve Conflicts (Mashaari Priority)
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

                // Accounting Engine Integration
                // Determine Bidder Team
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

                // Convert ScoreBreakdown to DetailedScore
                const usDetailed: DetailedScore = {
                    aklat: 0, ardh: 0,
                    mashaari: result.us.projectPoints,
                    abnat: result.us.rawCardPoints,
                    result: result.us.gamePoints,
                    projects: [], // Populate if needed
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
                    // baida: result.baida // Removed as it doesn't exist in RoundResult
                }];

                const globalUs = prev.matchScores.us + result.us.gamePoints;
                const globalThem = prev.matchScores.them + result.them.gamePoints;

                // Game Over Check (152)
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

                // Next Round
                setTimeout(() => startNewRound((prev.dealerIndex + 1) % 4, { us: globalUs, them: globalThem }), 1500);

                return {
                    ...prev,
                    teamScores: { us: currentUsRaw, them: currentThemRaw }, // Show final raw briefly
                    matchScores: { us: globalUs, them: globalThem },
                    roundHistory: newHistory,
                    tableCards: [],
                    isRoundTransitioning: true
                };
            }

            // Phase IV: Populate lastTrick for Sweep Animation
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

    // Effect to clear lastTrick after animation (Phase IV)
    useEffect(() => {
        if (gameState.lastTrick) {
            const timer = setTimeout(() => {
                setGameState(prev => ({ ...prev, lastTrick: null }));
            }, 1000); // Animation duration
            return () => clearTimeout(timer);
        }
    }, [gameState.lastTrick]);

    // Effect to trigger completeTrick
    useEffect(() => {
        if (gameState.isTrickTransitioning) {
            const timer = setTimeout(completeTrick, 600); // Speed up from 2000ms
            return () => clearTimeout(timer);
        }
    }, [gameState.isTrickTransitioning, completeTrick]);

    // Determine Project Reveal Delay
    useEffect(() => {
        if (gameState.isProjectRevealing) {
            const timer = setTimeout(() => {
                setGameState(prev => ({ ...prev, isProjectRevealing: false }));
            }, 800); // Wait for animation
            return () => clearTimeout(timer);
        }
    }, [gameState.isProjectRevealing]);

    // --- AKKA EFFECTS ---
    useEffect(() => {
        if (gameState.akkaState) {
            // Play Sound if not me (Me is handled by click handler optimistically, or we can just double play/debounce)
            // Ideally check if this timestamp is 'new' compared to last one.
            // For now, dependency on akkaState triggers this on any change (new object from backend).
            if (gameState.akkaState.claimer !== PlayerPosition.Bottom) {
                soundManager.playAkkaSound();
            }

            // Visual Feedback: Set Action Text for Claimer
            setGameState(prev => {
                const claimerIdx = prev.players.findIndex(p => p.position === prev.akkaState?.claimer);
                if (claimerIdx === -1) return prev;

                const newPlayers = [...prev.players];
                newPlayers[claimerIdx] = { ...newPlayers[claimerIdx], actionText: 'AKKA!' };
                return { ...prev, players: newPlayers };
            });

            // Clear Action Text after delay
            const timer = setTimeout(() => {
                setGameState(prev => {
                    const claimerIdx = prev.players.findIndex(p => p.position === prev.akkaState?.claimer);
                    if (claimerIdx === -1) return prev;
                    // Only clear if it is still AKKA
                    if (prev.players[claimerIdx].actionText === 'AKKA!') {
                        const newPlayers = [...prev.players];
                        newPlayers[claimerIdx] = { ...newPlayers[claimerIdx], actionText: undefined };
                        return { ...prev, players: newPlayers };
                    }
                    return prev;
                });
            }, 1500); // Reduced from 3000ms
            return () => clearTimeout(timer);
        }
    }, [gameState.akkaState]);

    // Handle Card Play
    const handleCardPlay = (playerIndex: number, cardIndex: number, metadata?: any) => {
        soundManager.playCardSound();
        setGameState(prev => {
            // DEFENSIVE: Ensure player and card exist
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
                if (idx === nextIndex && newTable.length < 4) return { ...p, isActive: true }; // Only activate next if trick not done
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

            // Log Turn Duration for Playing
            const now = performance.now();
            const duration = (now - turnStartTimeRef.current).toFixed(2);

            // Log Next Turn Wait Start
            const nextPlayer = newPlayers[nextIndex];
            // @ts-ignore
            import('../utils/devLogger').then(({ devLogger }) => {
                devLogger.log('PERF', `Turn Complete (Play): ${player.name}`, { duration: `${duration}ms` });
                if (roomId && nextPlayer.index !== 0) {
                    devLogger.log('PERF', `Waiting for Remote Player: ${nextPlayer.name} (Bot? ${nextPlayer.isBot})`);
                }
            });
            turnStartTimeRef.current = now;

            return { ...prev, players: newPlayers, tableCards: newTable, currentTurnIndex: nextIndex };
        });
    };

    const handleBiddingAction = (playerIndex: number, action: string, payload?: any) => {
        const speechText = action === 'PASS' ? 'Bass' : action === 'SUN' ? 'Sun' : action === 'HOKUM' ? 'Hokum' : action;
        speakAction(speechText);

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

            // PASS LOGIC
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
                // BUY LOGIC
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

                // Sort Hands
                newPlayers.forEach(p => {
                    const mode = action === 'SUN' ? 'SUN' : 'HOKUM';
                    p.hand = sortHand(p.hand, mode, selectedSuit);
                });

                addSystemMessage(`${newPlayers[playerIndex].name} اشترى ${action === 'SUN' ? 'صن' : 'حكم'}`);
                newPhase = GamePhase.Playing;

                // Detect Projects
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

            // Fallthrough for PASS (Standard Turn Change)
            newPlayers[nextIndex].isActive = true;

            // Log Turn Duration for Bidding
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

    const handleDoublingAction = (playerIndex: number) => {
        setGameState(prev => {
            let newLevel = prev.doublingLevel;
            if (newLevel === DoublingLevel.NORMAL) newLevel = DoublingLevel.DOUBLE;
            else if (newLevel === DoublingLevel.DOUBLE) newLevel = DoublingLevel.TRIPLE;

            addSystemMessage(`${prev.players[playerIndex].name} رفع المشاريع`);
            speakAction(newLevel === DoublingLevel.DOUBLE ? 'Sra' : 'Triple');

            return { ...prev, doublingLevel: newLevel, isLocked: prev.bid.type === 'HOKUM' };
        });
    };

    const handlePlayerAction = (action: string, payload?: any) => {
        if (isSendingAction && action !== 'QAYD_CANCEL' && action !== 'QAYD_CONFIRM') return; // Block duplicates, but allow Qayd Escape Hatch

        // @ts-ignore
        import('../utils/devLogger').then(({ devLogger }) => devLogger.log('HOOK', 'Player Action Triggered', { action, payload }));

        // Migration: If connected to Server (roomId exists), forward action.
        if (roomId) {
            setIsSendingAction(true); // Start blocking
            console.log(`[Client] Sending Action: ${action}`, payload);

            const onComplete = (res: any) => {
                setIsSendingAction(false); // Stop blocking
                if (!res.success) {
                    // Logic to handle failure (e.g. Toast)
                    addSystemMessage(`Action Failed: ${res.error || 'Unknown'}`);
                    soundManager.playErrorSound(); // Assuming this exists or needed
                }
            };

            if (action === 'PLAY') {
                // Determine card index if not provided (e.g. from UI?)
                // Payload usually has cardIndex from Table.tsx
                socketService.sendAction(roomId, 'PLAY', payload, onComplete);
            } else if (['SUN', 'HOKUM', 'PASS', 'ASHKAL'].includes(action)) {
                socketService.sendAction(roomId, 'BID', { action: action, suit: payload?.suit }, onComplete);
            } else if (action === 'DECLARE_PROJECT') {
                socketService.sendAction(roomId, 'DECLARE_PROJECT', payload, onComplete);
            } else if (action === 'SAWA_CLAIM') {
                socketService.sendAction(roomId, 'SAWA_CLAIM', {}, onComplete);
            } else if (action === 'SAWA_RESPONSE') {
                socketService.sendAction(roomId, 'SAWA_RESPONSE', payload, onComplete);
            } else if (action === 'NEXT_ROUND') {
                socketService.sendAction(roomId, 'NEXT_ROUND', {}, onComplete);
            } else if (action === 'QAYD') {
                // Disptue / Challenge
                socketService.sendAction(roomId, 'QAYD', payload, onComplete);
            } else if (action === 'QAYD_TRIGGER' || action === 'QAYD_ACCUSATION') {
                // Forensic Actions
                socketService.sendAction(roomId, action, payload, onComplete);
            } else if (action === 'DOUBLE') {
                console.warn("Doubling not fully implemented in Python yet.");
                setIsSendingAction(false);
            } else {
                console.warn("Unhandled Server Action - Clearing Spinner:", action);
                setIsSendingAction(false);
            }
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
                alert("Invalid Move!"); // Ideally use a toast
                return;
            }
            handleCardPlay(0, payload.cardIndex, payload.metadata);
        } else if (action === 'DOUBLE') {
            handleDoublingAction(0);
        }
    };

    // Bot Loop
    useEffect(() => {
        const heartbeat = setInterval(async () => {
            if (roomId) return; // Disable local bot loop if connected to server
            if (gameState.phase === GamePhase.GameOver || gameState.isTrickTransitioning || gameState.isProjectRevealing || gameState.isRoundTransitioning || isCuttingDeck || isBotThinking) return;
            if (gameState.currentTurnIndex === 0) return;

            setIsBotThinking(true);
            try {
                const playerPos = gameState.players[gameState.currentTurnIndex].position;
                const decision = await getBotDecision(gameState, playerPos);
                if (gameState.phase === GamePhase.Bidding) {
                    handleBiddingAction(gameState.currentTurnIndex, decision.action, { suit: decision.suit });
                } else if (gameState.phase === GamePhase.Playing) {
                    let trumpSuit = gameState.bid.type === 'HOKUM' ? (gameState.bid.suit || null) : null;
                    const mode = gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';
                    const botHand = sortHand(gameState.players[gameState.currentTurnIndex].hand, mode, trumpSuit);

                    let cardIdx = decision.cardIndex !== undefined && decision.cardIndex < botHand.length ? decision.cardIndex : 0;

                    // Safety
                    const cardToPlay = botHand[cardIdx];
                    if (gameState.bid.type === 'HOKUM' && !trumpSuit) trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;
                    const isValid = isValidMove(cardToPlay, botHand, gameState.tableCards, mode, trumpSuit, gameState.isLocked);

                    if (!isValid) {
                        const legalIdx = botHand.findIndex(c => isValidMove(c, botHand, gameState.tableCards, mode, trumpSuit, gameState.isLocked));
                        if (legalIdx !== -1) cardIdx = legalIdx;
                    }
                    handleCardPlay(gameState.currentTurnIndex, cardIdx);
                }
            } catch (e) {
                console.error("Bot Error", e);
            } finally {
                setIsBotThinking(false);
            }
        }, 1000);
        return () => clearInterval(heartbeat);
    }, [gameState, isCuttingDeck, isBotThinking]);

    // --- PHASE V: FAST FORWARD LOGIC ---
    const handleFastForward = useCallback(() => {
        addSystemMessage(">>> (Fast Forwarding...)");
        setGameState(prev => ({ ...prev, isFastForwarding: true, settings: { ...prev.settings, turnDuration: 0.1 } }));
    }, [addSystemMessage]);

    useEffect(() => {
        if (!gameState.isFastForwarding || gameState.phase !== GamePhase.Playing) return;
        if (gameState.isTrickTransitioning || gameState.isProjectRevealing || gameState.isRoundTransitioning) return;

        const timer = setTimeout(() => {
            // Force play for CURRENT player (even me)
            const idx = gameState.currentTurnIndex;
            const hand = gameState.players[idx].hand;

            // Allow bots to handle their own turn via bot loop? 
            // Better to force it here to guarantee speed.

            let trumpSuit = gameState.bid.type === 'HOKUM' ? (gameState.bid.suit || null) : null;
            const mode = gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';

            // Simple logic: Play HIGH card if possible to secure tricks (Solver is complex, just dump hand for visual)
            // Or just play ANY valid card.
            if (gameState.bid.type === 'HOKUM' && !trumpSuit) trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;

            const validIndices = hand.map((c, i) => isValidMove(c, hand, gameState.tableCards, mode, trumpSuit, gameState.isLocked) ? i : -1).filter(i => i !== -1);

            if (validIndices.length > 0) {
                // Pick random or first
                handleCardPlay(idx, validIndices[0]);
            }
        }, 150); // 150ms per card for visual tracking

        return () => clearTimeout(timer);
    }, [gameState.isFastForwarding, gameState.phase, gameState.currentTurnIndex, gameState.tableCards, gameState.isTrickTransitioning]); // Dep array is key for loop

    // --- HELPER: ROTATE STATE ---
    const rotateGameState = useCallback((serverState: GameState, myIdx: number): GameState => {
        try {
            // Console log removed for performance


            if (!serverState || !serverState.players || serverState.players.length === 0) {
                console.error("[rotateGameState] Invalid Server State:", serverState);
                return INITIAL_GAME_STATE; // Return safe initial state instead of undefined
            }

            // 1. Rotate Players - DEFENSIVE: Ensure myIdx is valid
            const safeMyIdx = Math.max(0, Math.min(myIdx, serverState.players.length - 1));
            const rotatedPlayers = [
                ...serverState.players.slice(safeMyIdx),
                ...serverState.players.slice(0, safeMyIdx)
            ];

            // 2. Rotate Turn Index - DEFENSIVE: Use nullish coalescing
            const currentTurn = serverState.currentTurnIndex ?? 0;
            const dealerIdx = serverState.dealerIndex ?? 0;
            const rotatedTurnIndex = (currentTurn - safeMyIdx + 4) % 4;
            const rotatedDealerIndex = (dealerIdx - safeMyIdx + 4) % 4;

            // DEBUG ROTATION
            if (serverState.phase === 'PLAYING' || serverState.phase === 'BIDDING') {
                // @ts-ignore
                import('../utils/devLogger').then(({ devLogger }) =>
                    devLogger.log('HOOK', 'Rotation Calc', { serverTurn: currentTurn, myIdx: safeMyIdx, rotatedTurn: rotatedTurnIndex })
                );
            }

            const serverPosOrder = ['Bottom', 'Right', 'Top', 'Left'];
            const frontendPosOrder = [PlayerPosition.Bottom, PlayerPosition.Right, PlayerPosition.Top, PlayerPosition.Left];

            const rotatePos = (pos: any): PlayerPosition => {
                const sIdx = serverPosOrder.indexOf(pos);
                if (sIdx === -1) return pos;
                const relativeIdx = (sIdx - myIdx + 4) % 4;
                return frontendPosOrder[relativeIdx];
            };

            const newPlayers = rotatedPlayers.map(p => ({
                ...p,
                position: rotatePos(p?.position)
            }));

            const newTableCards = (serverState.tableCards || []).map(tc => ({
                ...tc,
                playedBy: rotatePos(tc?.playedBy)
            }));

            const newBid = {
                ...serverState.bid,
                bidder: serverState.bid.bidder ? rotatePos(serverState.bid.bidder) : null
            };

            const newDeclarations: any = {};
            const declarations = serverState.declarations || {};
            Object.keys(declarations).forEach(posKey => {
                const newKey = rotatePos(posKey);
                const projectList = declarations[posKey] || [];
                newDeclarations[newKey] = projectList.map((d: DeclaredProject) => ({
                    ...d,
                    owner: rotatePos(d?.owner)
                }));
            });

            // Last Trick mapped - DEFENSIVE: Check if cards array exists
            let newLastTrick = null;
            if (serverState.lastTrick && serverState.lastTrick.cards) {
                newLastTrick = {
                    cards: serverState.lastTrick.cards.map(c => ({ ...c, playedBy: rotatePos(c?.playedBy) })),
                    winner: rotatePos(serverState.lastTrick.winner)
                };
            }

            // Rotate Akka State
            let newAkkaState = null;
            if (serverState.akkaState) {
                newAkkaState = {
                    ...serverState.akkaState,
                    claimer: rotatePos(serverState.akkaState.claimer)
                };
            }

            return {
                ...serverState,
                players: newPlayers,
                currentTurnIndex: rotatedTurnIndex,
                dealerIndex: rotatedDealerIndex,
                tableCards: newTableCards,
                bid: newBid,
                declarations: newDeclarations,
                lastTrick: newLastTrick,
                sawaState: serverState.sawaState, // SAWA is global usually, or position based? It has 'claimer' pos.
                qaydState: serverState.qaydState, // Global state
                akkaState: newAkkaState
            };
        } catch (e) {
            console.error("[rotateGameState] CRITICAL ERROR:", e);
            throw e; // Re-throw to be caught by caller
        }
    }, []);

    // --- SOCKET LISTENER ---
    useEffect(() => {
        if (!roomId) return;

        const cleanupUpdate = socketService.onGameUpdate((newGameState) => {
            const rotatedState = rotateGameState(newGameState, myIndexRef.current);
            setGameState(prev => ({ ...rotatedState, settings: prev.settings }));
        });

        const cleanupStart = socketService.onGameStart((newGameState) => {
            console.log("[useGameState] Received Game Start!", newGameState);
            const rotatedState = rotateGameState(newGameState, myIndexRef.current);
            setGameState(prev => ({ ...rotatedState, settings: prev.settings }));
        });

        return () => {
            if (cleanupUpdate) cleanupUpdate();
            if (cleanupStart) cleanupStart();
        };

    }, [roomId, rotateGameState]);

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
            soundManager.playWinSound();
        }
    };

    const calculateFinalScoreExport = calculateFinalScore; // Re-export if needed or used internally only

    return {
        gameState,
        setGameState,
        messages,
        userProfile,
        setUserProfile,
        handlePurchase,
        isCuttingDeck,
        isSendingAction,
        handlePlayerAction,
        handleDebugAction: (action: string, pl?: any) => {
            if (roomId) socketService.sendDebugAction(roomId, action, pl);
            else if (action === 'TOGGLE_DEBUG') {
                setGameState(prev => ({ ...prev, settings: { ...prev.settings, isDebug: pl.enable, turnDuration: pl.enable ? 99999 : 30 } }));
                addSystemMessage(`Debug Mode: ${pl.enable ? 'ON' : 'OFF'}`);
            }
        },
        updateSettings: (newSettings: any) => {
            setGameState(prev => ({ ...prev, settings: newSettings }));
            if (roomId) {
                // Sync with Backend
                socketService.sendAction(roomId, 'UPDATE_SETTINGS', newSettings);
            }
        },
        startNewRound,
        addSystemMessage,
        joinGame: (rid: string, idx: number, init: GameState) => {
            setRoomId(rid);
            setMyIndex(idx);
            const rotated = rotateGameState(init, idx);
            setGameState(prev => ({ ...rotated, settings: prev.settings }));
        },
        addBot: () => {
            if (roomId) {
                socketService.addBot(roomId, (res) => {
                    if (res.success) addSystemMessage("Bot added!");
                    else addSystemMessage(`Failed to add bot: ${res.error}`);
                });
            }
        },
        roomId, // Phase VII
        handleFastForward // Phase V
    };
};
