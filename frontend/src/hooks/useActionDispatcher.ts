import { useCallback, useEffect } from 'react';
import { GameState, GamePhase, GameSettings, Suit } from '../types';
import { isValidMove } from '../utils/gameLogic';

interface UseActionDispatcherArgs {
    gameState: GameState;
    setGameState: React.Dispatch<React.SetStateAction<GameState>>;
    addSystemMessage: (text: string) => void;
    playErrorSound: () => void;
    // Sub-hook handlers
    handleBiddingAction: (playerIndex: number, action: string, payload?: Record<string, unknown>) => void;
    handleCardPlay: (playerIndex: number, cardIndex: number, metadata?: Record<string, unknown>) => void;
    handleDoublingAction: (playerIndex: number) => void;
    // Socket
    roomId: string | null;
    isSendingAction: boolean;
    sendAction: (action: string, payload?: any, callback?: (res: any) => void) => void;
    sendDebugAction: (action: string, payload?: any) => void;
}

export const useActionDispatcher = ({
    gameState,
    setGameState,
    addSystemMessage,
    playErrorSound,
    handleBiddingAction,
    handleCardPlay,
    handleDoublingAction,
    roomId,
    isSendingAction,
    sendAction,
    sendDebugAction,
}: UseActionDispatcherArgs) => {

    // --- MAIN ACTION DISPATCHER ---
    const handlePlayerAction = (action: string, payload?: any) => {
        // Block duplicates except Qayd escape hatch
        if (isSendingAction && !action.startsWith('QAYD')) return;

        // @ts-ignore - dynamic import for dev logger
        import('../utils/devLogger').then(({ devLogger }) => devLogger.log('HOOK', 'Player Action Triggered', { action, payload }));

        // If connected to server, forward action via socket
        if (roomId) {
            sendAction(action, payload, (res: { success: boolean; error?: string }) => {
                if (!res.success) {
                    addSystemMessage(`Action Failed: ${res.error || 'Unknown'}`);
                    playErrorSound();
                }
            });
            return;
        }

        // --- LEGACY LOCAL LOGIC (Offline) ---
        if (gameState.currentTurnIndex !== 0) return;
        if (gameState.phase === GamePhase.Bidding) {
            handleBiddingAction(0, action, payload);
        } else if (gameState.phase === GamePhase.Playing && action === 'PLAY') {
            const card = gameState.players[0].hand[payload?.cardIndex as number];
            let trumpSuit: Suit | null = null;
            if (gameState.bid.type === 'HOKUM') trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;

            if (!isValidMove(card, gameState.players[0].hand, gameState.tableCards, gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM', trumpSuit, gameState.isLocked)) {
                alert("Invalid Move!");
                return;
            }
            handleCardPlay(0, payload?.cardIndex as number, payload?.metadata as Record<string, unknown>);
        } else if (action === 'DOUBLE') {
            handleDoublingAction(0);
        }
    };

    // --- FAST FORWARD LOGIC ---
    const handleFastForward = useCallback(() => {
        addSystemMessage(">>> (Fast Forwarding...)");
        setGameState(prev => ({ ...prev, isFastForwarding: true, settings: { ...prev.settings, turnDuration: 0.1 } }));
    }, [addSystemMessage, setGameState]);

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
    }, [gameState.isFastForwarding, gameState.phase, gameState.currentTurnIndex, gameState.tableCards, gameState.isTrickTransitioning, handleCardPlay]);

    // --- DEBUG / SETTINGS ---
    const handleDebugAction = (action: string, pl?: any) => {
        if (roomId) sendDebugAction(action, pl);
        else if (action === 'TOGGLE_DEBUG') {
            setGameState(prev => ({ ...prev, settings: { ...prev.settings, isDebug: pl?.enable as boolean, turnDuration: pl?.enable ? 99999 : 30 } }));
            addSystemMessage(`Debug Mode: ${pl?.enable ? 'ON' : 'OFF'}`);
        }
    };

    const updateSettings = (newSettings: any) => {
        setGameState(prev => ({ ...prev, settings: newSettings }));
        if (roomId) {
            sendAction('UPDATE_SETTINGS', newSettings);
        }
    };

    return {
        handlePlayerAction,
        handleFastForward,
        handleDebugAction,
        updateSettings,
    };
};
