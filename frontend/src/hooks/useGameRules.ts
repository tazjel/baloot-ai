
import { useMemo } from 'react';
import { GameState, Player, GamePhase, CardModel, ProjectType } from '../types';
import { detectProjects, sortHand, isValidMove } from '../utils/gameLogic';

export const useGameRules = (
    gameState: GameState,
    me: Player | undefined
) => {
    // 1. Projects Scanning
    const availableProjects = useMemo(() => {
        if (
            gameState.phase === GamePhase.Playing &&
            gameState.currentTurnIndex === 0 &&
            me?.hand &&
            me.hand.length === 8
        ) {
            const projects = detectProjects(me.hand, me.position, gameState.trumpSuit);
            // Return unique types
            return Array.from(new Set(projects.map(p => p.type)));
        }
        return [];
    }, [gameState.phase, gameState.currentTurnIndex, me?.hand, gameState.trumpSuit, me?.position]);

    // 2. Card Validation
    // NOTE: validation is PERMISSIVE to allow Qayd (Cheating/Mistakes) to occur.
    // If we enforced strict rules here, users couldn't make illegal moves.
    const isCardPlayable = (card: CardModel) => {
        if (gameState.phase !== GamePhase.Playing) return false;
        if (gameState.currentTurnIndex !== me?.index) return false;
        return true;
    };

    // Helper to check if a move IS checking rules (for UI warnings maybe)
    const checkMoveLegality = (card: CardModel) => {
        return isValidMove(
            card,
            me?.hand || [],
            gameState.tableCards || [],
            (gameState.gameMode as 'SUN' | 'HOKUM') || 'SUN',
            gameState.trumpSuit || null,
            gameState.isLocked,
            true
        );
    }

    // 3. Sorted Hand
    const sortedHand = useMemo(() => {
        if (!me?.hand) return [];
        return sortHand(me.hand, (gameState.gameMode as 'SUN' | 'HOKUM') || 'SUN', gameState.trumpSuit);
    }, [me?.hand, gameState.gameMode, gameState.trumpSuit]);

    return {
        availableProjects,
        isCardPlayable,
        checkMoveLegality,
        sortedHand
    };
};
