import { useEffect, useRef } from 'react';
import { GameState, GamePhase, DoublingLevel, Suit } from '../types';
import { isValidMove } from '../utils/gameLogic';

interface UsePlayingLogicArgs {
    gameState: GameState;
    setGameState: React.Dispatch<React.SetStateAction<GameState>>;
    addSystemMessage: (text: string) => void;
    playCardSound: () => void;
    speakAction: (text: string) => void;
    roomId: string | null;
    handleBiddingAction: (playerIndex: number, action: string, payload?: any) => void;
    turnStartTimeRef: React.MutableRefObject<number>;
}

export const usePlayingLogic = ({
    gameState,
    setGameState,
    addSystemMessage,
    playCardSound,
    speakAction,
    roomId,
    handleBiddingAction,
    turnStartTimeRef,
}: UsePlayingLogicArgs) => {

    // --- CARD PLAY HANDLER ---
    const handleCardPlay = (playerIndex: number, cardIndex: number, metadata?: any) => {
        playCardSound();
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
            // @ts-ignore - dynamic import for dev logger
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

    // --- DOUBLING HANDLER ---
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

    // --- TURN TIMER ENFORCEMENT ---
    useEffect(() => {
        if (gameState.currentTurnIndex !== 0) return;
        if (gameState.phase !== GamePhase.Bidding && gameState.phase !== GamePhase.Playing) return;
        if (gameState.settings.turnDuration > 100) return;
        if (roomId) return; // Server is authority

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
    }, [gameState.currentTurnIndex, gameState.phase, gameState.settings.turnDuration, roomId]);

    return {
        handleCardPlay,
        handleDoublingAction,
    };
};
