import { useEffect, useRef, useState } from 'react';
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

    // Use refs so the heartbeat interval reads current values without restarting
    const gameStateRef = useRef(gameState);
    const isBotThinkingRef = useRef(false);
    const isCuttingDeckRef = useRef(isCuttingDeck);
    const onBotActionRef = useRef(onBotAction);

    useEffect(() => { gameStateRef.current = gameState; }, [gameState]);
    useEffect(() => { isCuttingDeckRef.current = isCuttingDeck; }, [isCuttingDeck]);
    useEffect(() => { onBotActionRef.current = onBotAction; }, [onBotAction]);

    /**
     * Bot Heartbeat Loop
     * - Only runs in offline mode (no roomId)
     * - Checks every 1 second if it's a bot's turn
     * - Makes decision and triggers action via callback
     * - Uses refs to avoid restarting interval on every state change
     */
    useEffect(() => {
        // Disable bot loop if connected to server
        if (roomId) return;

        const heartbeat = setInterval(async () => {
            const gs = gameStateRef.current;

            // Skip if game is paused or transitioning
            if (
                gs.phase === GamePhase.GameOver ||
                gs.isTrickTransitioning ||
                gs.isProjectRevealing ||
                gs.isRoundTransitioning ||
                isCuttingDeckRef.current ||
                isBotThinkingRef.current
            ) {
                return;
            }

            // Skip if it's human player's turn (index 0)
            if (gs.currentTurnIndex === 0) return;

            isBotThinkingRef.current = true;
            setIsBotThinking(true);

            try {
                const currentPlayer = gs.players[gs.currentTurnIndex];
                const playerPos = currentPlayer.position;

                // Get bot decision from AI service
                const decision = await getBotDecision(gs, playerPos);

                // Execute bot action based on phase
                if (gs.phase === GamePhase.Bidding) {
                    onBotActionRef.current(gs.currentTurnIndex, decision.action, { suit: decision.suit });
                } else if (gs.phase === GamePhase.Playing) {
                    // Validate bot's card choice
                    let trumpSuit = gs.bid.type === 'HOKUM' ? (gs.bid.suit || null) : null;
                    const mode = gs.bid.type === 'SUN' ? 'SUN' : 'HOKUM';
                    const botHand = sortHand(currentPlayer.hand, mode, trumpSuit);

                    let cardIdx = decision.cardIndex !== undefined && decision.cardIndex < botHand.length
                        ? decision.cardIndex
                        : 0;

                    // Safety check: Ensure card is valid
                    const cardToPlay = botHand[cardIdx];
                    if (gs.bid.type === 'HOKUM' && !trumpSuit) {
                        trumpSuit = gs.bid.suit || gs.floorCard?.suit || Suit.Spades;
                    }

                    const isValid = isValidMove(
                        cardToPlay,
                        botHand,
                        gs.tableCards,
                        mode,
                        trumpSuit,
                        gs.isLocked
                    );

                    // If invalid, find first legal card
                    if (!isValid) {
                        const legalIdx = botHand.findIndex(c =>
                            isValidMove(c, botHand, gs.tableCards, mode, trumpSuit, gs.isLocked)
                        );
                        if (legalIdx !== -1) cardIdx = legalIdx;
                    }

                    onBotActionRef.current(gs.currentTurnIndex, 'PLAY', { cardIndex: cardIdx });
                }
            } catch (e) {
                console.error("[useLocalBot] Bot Error:", e);
            } finally {
                isBotThinkingRef.current = false;
                setIsBotThinking(false);
            }
        }, 1000); // Check every second

        return () => clearInterval(heartbeat);
    }, [roomId]); // Only restart interval when roomId changes (online ↔ offline)

    return { isBotThinking };
};
