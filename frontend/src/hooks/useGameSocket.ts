import { useCallback, useEffect, useRef, useState } from 'react';
import { GameState, GamePhase, DoublingLevel, PlayerPosition, DeclaredProject } from '../types';
import socketService from '../services/SocketService';
import { devLogger } from '../utils/devLogger';

const INITIAL_GAME_STATE: GameState = {
    players: [],
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
    settings: { turnDuration: 99999, strictMode: true, soundEnabled: true, gameSpeed: 'NORMAL', cardLanguage: 'EN' },
    lastTrick: null
};

interface UseGameSocketReturn {
    roomId: string | null;
    myIndex: number;
    isSendingAction: boolean;
    joinGame: (rid: string, idx: number, init: GameState) => void;
    sendAction: (action: string, payload?: any, onComplete?: (res: any) => void) => void;
    addBot: (onComplete?: (res: any) => void) => void;
    sendDebugAction: (action: string, payload?: any) => void;
    onGameUpdate: (callback: (state: GameState) => void) => void;
    rotateGameState: (serverState: GameState, myIdx: number) => GameState;
}

/**
 * useGameSocket - Manages all socket.io communication with the backend
 * 
 * Responsibilities:
 * - Connection management (roomId, myIndex)
 * - Action dispatching (play, bid, etc.)
 * - Game state rotation (server → client perspective)
 * - Socket event listeners (onGameUpdate, onGameStart)
 */
export const useGameSocket = (): UseGameSocketReturn => {
    const [roomId, setRoomId] = useState<string | null>(null);
    const [myIndex, setMyIndex] = useState<number>(0);
    const myIndexRef = useRef(0);
    const [isSendingAction, setIsSendingAction] = useState(false);
    
    // Callbacks storage for game updates
    const gameUpdateCallbackRef = useRef<((state: GameState) => void) | null>(null);

    // Keep myIndexRef in sync
    useEffect(() => {
        myIndexRef.current = myIndex;
    }, [myIndex]);

    /**
     * Rotate game state from server perspective to client perspective
     * Server uses absolute indices (0,1,2,3), client always sees themselves as index 0
     */
    const rotateGameState = useCallback((serverState: GameState, myIdx: number): GameState => {
        try {
            if (!serverState || !serverState.players || serverState.players.length === 0) {
                console.error("[rotateGameState] Invalid Server State:", serverState);
                return INITIAL_GAME_STATE;
            }

            // Validate myIdx
            const safeMyIdx = Math.max(0, Math.min(myIdx, serverState.players.length - 1));
            
            // 1. Rotate Players Array
            const rotatedPlayers = [
                ...serverState.players.slice(safeMyIdx),
                ...serverState.players.slice(0, safeMyIdx)
            ];

            // 2. Rotate Turn and Dealer Indices
            const currentTurn = serverState.currentTurnIndex ?? 0;
            const dealerIdx = serverState.dealerIndex ?? 0;
            const rotatedTurnIndex = (currentTurn - safeMyIdx + 4) % 4;
            const rotatedDealerIndex = (dealerIdx - safeMyIdx + 4) % 4;

            // 3. Position Mapping (Server → Client)
            const serverPosOrder = ['Bottom', 'Right', 'Top', 'Left'];
            const frontendPosOrder = [PlayerPosition.Bottom, PlayerPosition.Right, PlayerPosition.Top, PlayerPosition.Left];

            const rotatePos = (pos: any): PlayerPosition => {
                const sIdx = serverPosOrder.indexOf(pos);
                if (sIdx === -1) return pos;
                const relativeIdx = (sIdx - myIdx + 4) % 4;
                return frontendPosOrder[relativeIdx];
            };

            // 4. Rotate All Position References
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

            // Rotate Last Trick
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
                sawaState: serverState.sawaState,
                qaydState: serverState.qaydState,
                akkaState: newAkkaState
            };
        } catch (e) {
            console.error("[rotateGameState] CRITICAL ERROR:", e);
            return INITIAL_GAME_STATE;
        }
    }, []);

    /**
     * Join a game room
     */
    const joinGame = useCallback((rid: string, idx: number, init: GameState) => {
        setRoomId(rid);
        setMyIndex(idx);
        
        // Rotate initial state and trigger callback
        const rotated = rotateGameState(init, idx);
        if (gameUpdateCallbackRef.current) {
            gameUpdateCallbackRef.current(rotated);
        }
    }, [rotateGameState]);

    /**
     * Send action to server with optimistic locking
     */
    const sendAction = useCallback((action: string, payload?: any, onComplete?: (res: any) => void) => {
        if (!roomId) {
            console.warn("[useGameSocket] Cannot send action - not connected to room");
            return;
        }

        // Block duplicate actions (except all Qayd multi-step wizard actions)
        if (isSendingAction && !action.startsWith('QAYD')) {
            console.warn("[useGameSocket] Action blocked - already sending");
            return;
        }

        setIsSendingAction(true);
        devLogger.log('SOCKET', `Sending Action: ${action}`, payload);

        const wrappedCallback = (res: any) => {
            setIsSendingAction(false);
            if (onComplete) onComplete(res);
        };

        // Route actions to appropriate socket service methods
        if (action === 'PLAY') {
            socketService.sendAction(roomId, 'PLAY', payload, wrappedCallback);
        } else if (['SUN', 'HOKUM', 'PASS', 'ASHKAL'].includes(action)) {
            socketService.sendAction(roomId, 'BID', { action: action, suit: payload?.suit }, wrappedCallback);
        } else if (action === 'DECLARE_PROJECT') {
            socketService.sendAction(roomId, 'DECLARE_PROJECT', payload, wrappedCallback);
        } else if (action === 'SAWA_CLAIM') {
            socketService.sendAction(roomId, 'SAWA_CLAIM', {}, wrappedCallback);
        } else if (action === 'SAWA_RESPONSE') {
            socketService.sendAction(roomId, 'SAWA_RESPONSE', payload, wrappedCallback);
        } else if (action === 'NEXT_ROUND') {
            socketService.sendAction(roomId, 'NEXT_ROUND', {}, wrappedCallback);
        } else if (action.startsWith('QAYD')) {
            socketService.sendAction(roomId, action, payload, wrappedCallback);
        } else if (action === 'DOUBLE') {
            console.warn("[useGameSocket] Doubling not fully implemented in Python yet.");
            setIsSendingAction(false);
        } else if (action === 'UPDATE_SETTINGS') {
            socketService.sendAction(roomId, 'UPDATE_SETTINGS', payload, wrappedCallback);
        } else {
            console.warn("[useGameSocket] Unhandled Server Action:", action);
            setIsSendingAction(false);
        }
    }, [roomId, isSendingAction]);

    /**
     * Add bot to game
     */
    const addBot = useCallback((onComplete?: (res: any) => void) => {
        if (!roomId) return;
        socketService.addBot(roomId, onComplete || (() => {}));
    }, [roomId]);

    /**
     * Send debug action
     */
    const sendDebugAction = useCallback((action: string, payload?: any) => {
        if (!roomId) return;
        socketService.sendDebugAction(roomId, action, payload);
    }, [roomId]);

    /**
     * Register callback for game updates
     */
    const onGameUpdate = useCallback((callback: (state: GameState) => void) => {
        gameUpdateCallbackRef.current = callback;
    }, []);

    /**
     * Socket Event Listeners
     */
    useEffect(() => {
        if (!roomId) return;

        const cleanupUpdate = socketService.onGameUpdate((newGameState) => {
            const rotatedState = rotateGameState(newGameState, myIndexRef.current);
            if (gameUpdateCallbackRef.current) {
                gameUpdateCallbackRef.current(rotatedState);
            }
        });

        const cleanupStart = socketService.onGameStart((newGameState) => {
            devLogger.log('SOCKET', 'Received Game Start!', newGameState);
            const rotatedState = rotateGameState(newGameState, myIndexRef.current);
            if (gameUpdateCallbackRef.current) {
                gameUpdateCallbackRef.current(rotatedState);
            }
        });

        return () => {
            if (cleanupUpdate) cleanupUpdate();
            if (cleanupStart) cleanupStart();
        };
    }, [roomId, rotateGameState]);

    return {
        roomId,
        myIndex,
        isSendingAction,
        joinGame,
        sendAction,
        addBot,
        sendDebugAction,
        onGameUpdate,
        rotateGameState
    };
};
