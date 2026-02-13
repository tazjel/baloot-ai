import { useState, useEffect, useRef, useCallback } from 'react';
import { GameState, GamePhase, PlayerPosition, DoublingLevel, UserProfile } from '../types';
import { calculateFinalScore } from '../utils/gameLogic';
import { AVATARS, INITIAL_PLAYERS as PLAYER_DEFAULTS } from '../constants';

// Composed hooks
import { useGameSocket } from './useGameSocket';
import { useGameAudio } from './useGameAudio';
import { useLocalBot } from './useLocalBot';
import { useRoundManager } from './useRoundManager';
import { useBiddingLogic } from './useBiddingLogic';
import { usePlayingLogic } from './usePlayingLogic';
import { useActionDispatcher } from './useActionDispatcher';
import { AccountingEngine } from '../services/AccountingEngine';

const INITIAL_GAME_STATE: GameState = {
    players: [
        { ...PLAYER_DEFAULTS[0], hand: [], score: 0, isDealer: false, isActive: true, index: 0 },
        { ...PLAYER_DEFAULTS[1], hand: [], score: 0, isDealer: false, isActive: false, index: 1 },
        { ...PLAYER_DEFAULTS[2], hand: [], score: 0, isDealer: false, isActive: false, index: 2 },
        { ...PLAYER_DEFAULTS[3], hand: [], score: 0, isDealer: true, isActive: false, index: 3 },
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
    settings: { turnDuration: 5, strictMode: true, soundEnabled: true, gameSpeed: 'NORMAL', cardLanguage: 'EN' },
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

    // ===== HELPERS =====
    const addSystemMessage = useCallback((text: string) => {
        setMessages(prev => [...prev, { sender: "النظام", text }]);
    }, []);

    // ===== INFRASTRUCTURE HOOKS =====
    const socket = useGameSocket();
    const audio = useGameAudio(gameState);

    // ===== GAME LOGIC HOOKS =====
    const { startNewRound } = useRoundManager({
        gameState,
        setGameState,
        addSystemMessage,
        playAkkaSound: audio.playAkkaSound,
    });

    const { handleBiddingAction } = useBiddingLogic({
        gameState,
        setGameState,
        addSystemMessage,
        speakAction: audio.speakAction,
        startNewRound,
        turnStartTimeRef,
    });

    const { handleCardPlay, handleDoublingAction } = usePlayingLogic({
        gameState,
        setGameState,
        addSystemMessage,
        playCardSound: audio.playCardSound,
        speakAction: audio.speakAction,
        roomId: socket.roomId,
        handleBiddingAction,
        turnStartTimeRef,
    });

    const { handlePlayerAction, handleFastForward, handleDebugAction, updateSettings } = useActionDispatcher({
        gameState,
        setGameState,
        addSystemMessage,
        playErrorSound: audio.playErrorSound,
        handleBiddingAction,
        handleCardPlay,
        handleDoublingAction,
        roomId: socket.roomId,
        isSendingAction: socket.isSendingAction,
        sendAction: socket.sendAction,
        sendDebugAction: socket.sendDebugAction,
    });

    // ===== LOCAL BOT =====
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
    useEffect(() => {
        socket.onGameUpdate((newState) => {
            setGameState(prev => ({ ...newState, settings: prev.settings }));
        });
    }, [socket]);

    // ===== USER PROFILE PERSISTENCE =====
    useEffect(() => {
        localStorage.setItem('baloot_user_profile', JSON.stringify(userProfile));
    }, [userProfile]);

    // ===== LOGGING EFFECT =====
    useEffect(() => {
        if (!gameState.players || !gameState.players[gameState.currentTurnIndex]) return;

        turnStartTimeRef.current = performance.now();
        const player = gameState.players[gameState.currentTurnIndex];

        // @ts-ignore
        import('../utils/devLogger').then(({ devLogger }) => {
            devLogger.log('PERF', `New Turn: ${player.name} (Index ${gameState.currentTurnIndex})`);
        });
    }, [gameState.currentTurnIndex]);

    // ===== STORE LOGIC =====
    const handlePurchase = (itemId: string, cost: number) => {
        if (AccountingEngine.Purchase.canAfford(userProfile, cost)) {
            setUserProfile(prev => ({ 
                ...prev, 
                coins: AccountingEngine.Purchase.processTransaction(prev.coins, cost)
            }));
            audio.playWinSound();
        }
    };

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
        handleDebugAction,
        updateSettings,
        startNewRound,
        addSystemMessage,
        joinGame: socket.joinGame,
        addBot: socket.addBot,
        roomId: socket.roomId,
        handleFastForward,
        isBotThinking: bot.isBotThinking
    };
};
