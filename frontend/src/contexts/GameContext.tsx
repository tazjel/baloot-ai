import React, { createContext, useContext, ReactNode } from 'react';
import { useGameState } from '../hooks/useGameState';

/**
 * GameContext — Eliminates prop-drilling by providing game state + actions
 * to any component in the tree via useGameContext().
 *
 * Usage:
 *   // In App.tsx or top-level:
 *   <GameProvider>
 *     <App />
 *   </GameProvider>
 *
 *   // In any child component:
 *   const { gameState, handlePlayerAction } = useGameContext();
 */

// The shape of the context matches the return type of useGameState
type GameContextType = ReturnType<typeof useGameState>;

const GameContext = createContext<GameContextType | null>(null);

interface GameProviderProps {
    children: ReactNode;
}

/**
 * GameProvider wraps children and provides the full game state + actions.
 * Call useGameState() once here, and every descendant can use useGameContext().
 */
export const GameProvider: React.FC<GameProviderProps> = ({ children }) => {
    const gameState = useGameState();

    return (
        <GameContext.Provider value={gameState}>
            {children}
        </GameContext.Provider>
    );
};

/**
 * useGameContext — Access game state + actions from any component.
 * Must be used within a <GameProvider>.
 *
 * @throws Error if used outside GameProvider
 */
export const useGameContext = (): GameContextType => {
    const context = useContext(GameContext);
    if (!context) {
        throw new Error('useGameContext must be used within a <GameProvider>. Wrap your component tree with <GameProvider>.');
    }
    return context;
};

export default GameContext;
