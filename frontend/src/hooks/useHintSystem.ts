/**
 * useHintSystem — Manages AI hint state for the human player.
 *
 * Provides requestHint() to compute a hint on-demand and dismissHint() to hide it.
 * Auto-clears when the turn or phase changes.
 *
 * M17.2: AI Hint System
 */
import { useState, useCallback, useEffect } from 'react';
import { GameState, GamePhase, HintResult } from '../types';
import { getHint } from '../services/hintService';

interface UseHintSystemReturn {
    hint: HintResult | null;
    isHintVisible: boolean;
    requestHint: () => void;
    dismissHint: () => void;
}

export function useHintSystem(gameState: GameState): UseHintSystemReturn {
    const [hint, setHint] = useState<HintResult | null>(null);
    const [isHintVisible, setIsHintVisible] = useState(false);

    const isMyTurn = gameState.currentTurnIndex === 0;
    const hintsEnabled = gameState.settings?.showHints !== false;

    // Auto-dismiss when turn changes or phase changes
    useEffect(() => {
        setHint(null);
        setIsHintVisible(false);
    }, [gameState.currentTurnIndex, gameState.phase]);

    const requestHint = useCallback(() => {
        if (!isMyTurn || !hintsEnabled) return;
        const { phase, biddingPhase } = gameState;
        if (phase !== GamePhase.Bidding && phase !== GamePhase.Playing && biddingPhase !== 'GABLAK_WINDOW') return;

        const result = getHint(gameState);
        if (result) {
            setHint(result);
            setIsHintVisible(true);
        }
    }, [gameState, isMyTurn, hintsEnabled]);

    const dismissHint = useCallback(() => {
        setIsHintVisible(false);
    }, []);

    return { hint, isHintVisible, requestHint, dismissHint };
}
