
import { useState, useEffect } from 'react';
import { GameState } from '../types';

export type TensionLevel = 'low' | 'medium' | 'high' | 'critical';

export const useGameTension = (gameState: GameState | null) => {
    const [tension, setTension] = useState<TensionLevel>('low');
    const [bpm, setBpm] = useState(0); // 0 means no heartbeat

    useEffect(() => {
        if (!gameState) return;

        let level: TensionLevel = 'low';
        let newBpm = 0;

        if (!gameState.matchScores) return;

        const scoreUs = gameState.matchScores.us;
        const scoreThem = gameState.matchScores.them;
        const maxScore = Math.max(scoreUs, scoreThem);
        const diff = Math.abs(scoreUs - scoreThem);

        // 1. Critical: Endgame (Score > 145)
        if (maxScore >= 145) {
            level = 'critical';
            newBpm = 100; // Fast pounding
        }
        // 2. High: Late game (Score > 100) and Close (Diff < 20)
        else if (maxScore > 100 && diff < 20) {
            level = 'high';
            newBpm = 80;
        }
        // 3. Medium: Doubling is active or Sawa
        else if (gameState.phase === 'DOUBLING' || gameState.sawaState?.active) {
            level = 'medium';
            newBpm = 60;
        }

        setTension(level);
        setBpm(newBpm);

    }, [gameState]);

    return { tension, bpm };
};
