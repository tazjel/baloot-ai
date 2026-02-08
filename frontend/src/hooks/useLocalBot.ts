import { useEffect, useState } from 'react';
import { GameState, GamePhase, Suit } from '../types';
import { getBotDecision } from '../services/botService';
import { sortHand, isValidMove } from '../utils/gameLogic';

interface UseLocalBotReturn {
    isBotThinking: boolean;
}

interface UseLocalBotProps {
    gameState: GameState;
    roomId: string | null;
    isCuttingDeck: boolean;
    onBotAction: (playerIndex: number, action: string, payload?: any) => void;
}

/**
 * useLocalBot - Manages automated bot actions in offline mode
 * 
 * Responsibilities:
 * - Bot decision making (bidding & playing)
 * - Heartbeat loop for bot turns
 * - Disabled when connected to server (roomId exists)
 */
export const useLocalBot = ({
    gameState,
    roomId,
    isCuttingDeck,
    onBotAction
}: UseLocalBotProps): UseLocalBotReturn => {
    const [isBotThinking, setIsBotThinking] = useState(false);

    /**
     * Bot Heartbeat Loop
     * - Only runs in offline mode (no roomId)
     * - Checks every 1 second if it's a bot's turn
     * - Makes decision and triggers action via callback
     */
    useEffect(() => {
        // Disable bot loop if connected to server
        if (roomId) return;

        const heartbeat = setInterval(async () => {
            // Skip if game is paused or transitioning
            if (
                gameState.phase === GamePhase.GameOver ||
                gameState.isTrickTransitioning ||
                gameState.isProjectRevealing ||
                gameState.isRoundTransitioning ||
                isCuttingDeck ||
                isBotThinking
            ) {
                return;
            }

            // Skip if it's human player's turn (index 0)
            if (gameState.currentTurnIndex === 0) return;

            setIsBotThinking(true);

            try {
                const currentPlayer = gameState.players[gameState.currentTurnIndex];
                const playerPos = currentPlayer.position;

                // Get bot decision from AI service
                const decision = await getBotDecision(gameState, playerPos);

                // Execute bot action based on phase
                if (gameState.phase === GamePhase.Bidding) {
                    onBotAction(gameState.currentTurnIndex, decision.action, { suit: decision.suit });
                } else if (gameState.phase === GamePhase.Playing) {
                    // Validate bot's card choice
                    let trumpSuit = gameState.bid.type === 'HOKUM' ? (gameState.bid.suit || null) : null;
                    const mode = gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';
                    const botHand = sortHand(currentPlayer.hand, mode, trumpSuit);

                    let cardIdx = decision.cardIndex !== undefined && decision.cardIndex < botHand.length 
                        ? decision.cardIndex 
                        : 0;

                    // Safety check: Ensure card is valid
                    const cardToPlay = botHand[cardIdx];
                    if (gameState.bid.type === 'HOKUM' && !trumpSuit) {
                        trumpSuit = gameState.bid.suit || gameState.floorCard?.suit || Suit.Spades;
                    }
                    
                    const isValid = isValidMove(
                        cardToPlay,
                        botHand,
                        gameState.tableCards,
                        mode,
                        trumpSuit,
                        gameState.isLocked
                    );

                    // If invalid, find first legal card
                    if (!isValid) {
                        const legalIdx = botHand.findIndex(c =>
                            isValidMove(c, botHand, gameState.tableCards, mode, trumpSuit, gameState.isLocked)
                        );
                        if (legalIdx !== -1) cardIdx = legalIdx;
                    }

                    onBotAction(gameState.currentTurnIndex, 'PLAY', { cardIndex: cardIdx });
                }
            } catch (e) {
                console.error("[useLocalBot] Bot Error:", e);
            } finally {
                setIsBotThinking(false);
            }
        }, 1000); // Check every second

        return () => clearInterval(heartbeat);
    }, [
        gameState,
        roomId,
        isCuttingDeck,
        isBotThinking,
        onBotAction
    ]);

    return { isBotThinking };
};
